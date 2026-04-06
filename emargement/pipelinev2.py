"""
Pipeline d'extraction de listes d'émargement — v3
==================================================
Nouveautés v3 (détection signature)
-------------------------------------
Stratégie HYBRIDE en cascade :
  1. OpenCV rapide  : analyse densité pixels sombres + contours
                      → décision immédiate si confiance ≥ seuil
  2. Modèle vision  : fallback Ollama uniquement si CV ambigu
                      → économise ~80% des appels LLM

Mode --debug : sauvegarde les crops dans ./debug_crops/
               pour vérifier visuellement le découpage des cellules

Corrections bbox :
  - Auto-détection du système de coordonnées Docling (normalisé vs points)
  - Fallback : découpage par position relative dans la ligne si bbox absente

Usage
-----
python pipeline.py --dossier /chemin/vers/bureau_001
python pipeline.py --dossier /chemin/vers/bureau_001 --debug
python pipeline.py --dossier /chemin/vers/bureau_001 --modele qwen2-vl:2b
python pipeline.py --dossier /chemin/vers/bureau_001 --skip-vision
"""

import argparse
import base64
import datetime
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np
import requests
from PIL import Image
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

try:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        EasyOcrOptions, PdfPipelineOptions,
        TableFormerMode, TableStructureOptions,
    )
    from docling.document_converter import DocumentConverter, ImageFormatOption
    DOCLING_OK = True
except ImportError:
    print("⚠  Docling non installé. Lancez : pip install docling")
    DOCLING_OK = False


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

OLLAMA_URL    = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "moondream"
SUPPORTED_EXT = {".jpg", ".jpeg", ".png"}

SIGNATURE_PROMPT = (
    "This is a small crop from a French electoral roll. "
    "Does it contain a handwritten signature, initials, a paraph, "
    "or any handwritten ink mark? "
    "Answer with exactly one word: yes or no."
)

# ── Seuils détection CV ────────────────────────────────────────────────────
# Un crop est jugé "signé" si le % de pixels sombres dépasse INK_HIGH,
# "non signé" si inférieur à INK_LOW, "ambigu" entre les deux → fallback vision.
INK_LOW  = 0.008   # < 0.8 % de pixels sombres → non signé
INK_HIGH = 0.035   # > 3.5 % de pixels sombres → signé
# Seuil de binarisation (0-255) : pixels en dessous = encre
BINARIZE_THRESH = 100
# Taille minimale d'un contour pour compter comme tracé (en pixels²)
MIN_CONTOUR_AREA = 12


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE D'EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def _normalize_order(raw: str) -> str:
    cleaned = re.sub(r"(?<=\d)[.\s\u00a0-](?=\d)", "", raw.strip())
    digits  = re.sub(r"\D", "", cleaned)
    return digits.zfill(5) if 1 <= len(digits) <= 6 else ""

def _merge_nom_prenom(nom: str, prenom: str) -> str:
    nom    = nom.strip().upper()
    prenom = " ".join(p.capitalize() for p in prenom.strip().split())
    return f"{nom} {prenom}" if nom and prenom else (nom or prenom)

def _merge_date_lieu(date: str, lieu: str) -> str:
    date, lieu = date.strip(), lieu.strip()
    return f"{date} — {lieu}" if date and lieu else (date or lieu)

EXTRACTION_TEMPLATE: dict[str, dict[str, Any]] = {
    "numero_ordre": {
        "label":    "N° ordre",
        "patterns": [
            r"n[°o°][\s._-]*ord", r"num[ée]ro[\s._-]*ord",
            r"\border\b", r"^n[°o°]\s*$",
        ],
        "transform": _normalize_order,
    },
    "nom_prenom": {
        "label":    "Nom / Prénom",
        "sources":  ["_nom_raw", "_prenom_raw"],
        "transform": _merge_nom_prenom,
    },
    "adresse": {
        "label":    "Adresse de rattachement",
        "patterns": [r"adresse", r"rattachement", r"domicile", r"résidence"],
    },
    "date_lieu_naissance": {
        "label":    "Date et lieu de naissance",
        "sources":  ["_date_raw", "_lieu_raw"],
        "transform": _merge_date_lieu,
    },
    "a_emarge": {
        "label":    "A émargé",
        "patterns": [r"émarg", r"emarg", r"signature", r"sign\.", r"paraph"],
    },
}

_RAW_COL_PATTERNS: dict[str, list[str]] = {
    "_nom_raw":    [r"\bnom\b(?!.*pr[ée]nom)", r"patronyme", r"^nom\b"],
    "_prenom_raw": [r"pr[ée]nom"],
    "_date_raw":   [r"date.*naiss", r"naiss.*date", r"n[ée]\s+le", r"^date\b"],
    "_lieu_raw":   [r"lieu.*naiss", r"naiss.*lieu", r"n[ée][e]?\s+[àa]", r"^lieu\b"],
}

OUTPUT_FIELDS: list[tuple[str, str]] = [
    ("_bureau",             "Bureau de vote"),
    ("_source",             "Fichier source"),
    ("numero_ordre",        "N° ordre"),
    ("nom_prenom",          "Nom / Prénom"),
    ("adresse",             "Adresse de rattachement"),
    ("date_lieu_naissance", "Date et lieu de naissance"),
    ("a_emarge",            "A émargé"),
    ("_sign_method",        "Méthode détection"),   # colonne de traçabilité
]


# ══════════════════════════════════════════════════════════════════════════════
# DÉTECTION DE SIGNATURE — STRATÉGIE HYBRIDE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SignatureResult:
    verdict: str          # "oui" | "non" | "inconnu"
    method:  str          # "cv" | "vision" | "cv+vision" | "no_crop"
    confidence: float     # 0.0 → 1.0 (densité d'encre normalisée)


def preprocess_crop(img_bgr: np.ndarray) -> np.ndarray:
    """
    Prépare le crop pour la détection :
    - Conversion en niveaux de gris
    - CLAHE pour normaliser le contraste (utile sur photos sombres / mal éclairées)
    - Binarisation adaptative
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Normalisation du contraste
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(4, 4))
    gray  = clahe.apply(gray)

    # Binarisation globale d'Otsu (robuste au niveau de gris variable)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binary


def detect_signature_cv(img_bgr: np.ndarray) -> SignatureResult:
    """
    Détection classique via OpenCV.

    Critères combinés :
      1. Densité d'encre (% pixels sombres après binarisation)
      2. Nombre de contours significatifs (tracés distincts)
      3. Rapport largeur/hauteur des contours (les signatures sont larges)

    Retourne "oui" / "non" / "ambigu" selon la confiance.
    """
    if img_bgr is None or img_bgr.size == 0:
        return SignatureResult("inconnu", "cv", 0.0)

    binary = preprocess_crop(img_bgr)
    total  = binary.size
    ink    = int(np.sum(binary > 0))
    density = ink / total

    # Compter les contours significatifs
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    sig_contours = [c for c in contours if cv2.contourArea(c) >= MIN_CONTOUR_AREA]
    n_contours   = len(sig_contours)

    # Rapport largeur/hauteur de la bounding box globale des contours
    h_img, w_img = binary.shape
    aspect_ok    = False
    if sig_contours:
        all_pts = np.vstack(sig_contours)
        x, y, cw, ch = cv2.boundingRect(all_pts)
        aspect_ok = (cw / max(ch, 1)) > 1.5  # signature plus large que haute

    # Décision
    if density >= INK_HIGH and n_contours >= 2:
        verdict    = "oui"
        confidence = min(1.0, density / INK_HIGH)
    elif density <= INK_LOW or n_contours == 0:
        verdict    = "non"
        confidence = 1.0 - (density / INK_LOW) if density > 0 else 1.0
    else:
        # Zone ambiguë → renvoyer "ambigu" pour que le pipeline appelle la vision
        verdict    = "ambigu"
        confidence = density / INK_HIGH

    return SignatureResult(verdict, "cv", min(1.0, confidence))


def detect_signature_vision(img_bgr: np.ndarray, model: str) -> SignatureResult:
    """Appel au modèle vision Ollama."""
    _, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 92])
    b64    = base64.b64encode(buf.tobytes()).decode()
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": model, "prompt": SIGNATURE_PROMPT,
                  "images": [b64], "stream": False},
            timeout=45,
        )
        resp.raise_for_status()
        text = resp.json().get("response", "").strip().lower()
        verdict = "oui" if "yes" in text[:30] else ("non" if "no" in text[:30] else "inconnu")
        return SignatureResult(verdict, "vision", 0.5)
    except requests.exceptions.ConnectionError:
        print("  ⚠  Ollama non disponible")
        return SignatureResult("inconnu", "vision", 0.0)
    except Exception as e:
        print(f"  ⚠  Vision error : {e}")
        return SignatureResult("inconnu", "vision", 0.0)


def detect_signature(
    img_bgr: np.ndarray,
    model: str,
    ollama_ok: bool,
    debug_path: str | None = None,
) -> SignatureResult:
    """
    Pipeline de détection hybride :
      1. CV rapide
      2. Si ambigu ET ollama disponible → vision
      3. Sinon → résultat CV

    Si debug_path fourni, sauvegarde le crop annoté.
    """
    if img_bgr is None:
        return SignatureResult("inconnu", "no_crop", 0.0)

    cv_result = detect_signature_cv(img_bgr)

    if debug_path:
        _save_debug_crop(img_bgr, cv_result, debug_path)

    if cv_result.verdict == "ambigu":
        if ollama_ok:
            vis_result = detect_signature_vision(img_bgr, model)
            # Consensus : si les deux sont différents → inconnu
            if vis_result.verdict == cv_result.verdict:
                return SignatureResult(vis_result.verdict, "cv+vision", vis_result.confidence)
            elif vis_result.verdict != "inconnu":
                return SignatureResult(vis_result.verdict, "cv+vision", vis_result.confidence)
            else:
                return SignatureResult("inconnu", "cv+vision", 0.3)
        else:
            # Sans vision, on tranche par le seuil médian
            return SignatureResult(
                "oui" if cv_result.confidence >= 0.5 else "non",
                "cv", cv_result.confidence
            )

    return cv_result


def _save_debug_crop(img_bgr: np.ndarray, result: SignatureResult, path: str) -> None:
    """Sauvegarde le crop avec annotation (verdict + densité) pour inspection."""
    try:
        annotated = img_bgr.copy()
        color = (0, 180, 0) if result.verdict == "oui" else (0, 0, 200)
        label = f"{result.verdict} [{result.confidence:.2f}]"
        cv2.putText(annotated, label, (2, 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
        cv2.rectangle(annotated, (0, 0),
                      (annotated.shape[1]-1, annotated.shape[0]-1), color, 1)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        cv2.imwrite(path, annotated)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES BBOX DOCLING
# ══════════════════════════════════════════════════════════════════════════════

def resolve_bbox(bbox, img_w: int, img_h: int) -> tuple[int, int, int, int] | None:
    """
    Convertit une BoundingBox Docling en pixels (x0, y0, x1, y1).

    Docling peut retourner :
    - Coordonnées normalisées (0..1) : l, t, r, b ∈ [0, 1]
    - Coordonnées en points page     : valeurs > 1.0

    On détecte le système automatiquement.
    """
    if bbox is None:
        return None
    try:
        l, t, r, b = bbox.l, bbox.t, bbox.r, bbox.b

        # Détection : normalisé si toutes les coords ≤ 1.0
        if max(l, t, r, b) <= 1.0:
            x0, y0 = int(l * img_w), int(t * img_h)
            x1, y1 = int(r * img_w), int(b * img_h)
        else:
            # Coordonnées en points → conversion pixels
            # Docling utilise 72 dpi par défaut pour les images
            # Mais on peut déduire le facteur depuis les dimensions connues
            max_coord = max(r, b)
            # Heuristique : si les coords semblent être en points (< 1000)
            # on suppose une page A4 à 150 dpi = ~842×1191 pts
            # Sinon on suppose des pixels directs
            if max_coord < 100:
                # Probablement en % (0..100)
                x0, y0 = int(l / 100 * img_w), int(t / 100 * img_h)
                x1, y1 = int(r / 100 * img_w), int(b / 100 * img_h)
            elif max_coord < 2000:
                # Probablement en points typographiques (1 pt = 1/72 inch)
                # On normalise par rapport à la valeur max observée
                x0, y0 = int(l / max_coord * img_w), int(t / max_coord * img_h)
                x1, y1 = int(r / max_coord * img_w), int(b / max_coord * img_h)
            else:
                # Coordonnées en pixels directement
                x0, y0, x1, y1 = int(l), int(t), int(r), int(b)

        # Marge + clamp
        pad = 6
        x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
        x1, y1 = min(img_w, x1 + pad), min(img_h, y1 + pad)

        if (x1 - x0) < 8 or (y1 - y0) < 8:
            return None
        return x0, y0, x1, y1

    except Exception:
        return None


def crop_from_bbox(img_bgr: np.ndarray, bbox, img_w: int, img_h: int) -> np.ndarray | None:
    coords = resolve_bbox(bbox, img_w, img_h)
    if coords is None:
        return None
    x0, y0, x1, y1 = coords
    return img_bgr[y0:y1, x0:x1]


def crop_from_row_position(
    img_bgr: np.ndarray,
    row_bbox, img_w: int, img_h: int,
    col_fraction: float = 0.75, col_width: float = 0.12,
) -> np.ndarray | None:
    """
    Fallback quand la bbox de la cellule est absente :
    on estime la position de la colonne signature comme fraction
    de la largeur de la ligne (par défaut : dernier 12% de la ligne).
    """
    coords = resolve_bbox(row_bbox, img_w, img_h)
    if coords is None:
        return None
    rx0, ry0, rx1, ry1 = coords
    row_w = rx1 - rx0
    x0 = rx0 + int(row_w * col_fraction)
    x1 = rx0 + int(row_w * (col_fraction + col_width))
    x0, x1 = max(0, x0), min(img_w, x1)
    if (x1 - x0) < 8 or (ry1 - ry0) < 8:
        return None
    return img_bgr[ry0:ry1, x0:x1]


# ══════════════════════════════════════════════════════════════════════════════
# CLASSE DocumentExtractor
# ══════════════════════════════════════════════════════════════════════════════

class DocumentExtractor:
    def __init__(self, template: dict, converter: "DocumentConverter") -> None:
        self.template  = template
        self.converter = converter
        self._composed = {k: v for k, v in template.items() if "sources" in v}
        self._simple   = {k: v for k, v in template.items()
                          if "patterns" in v and "sources" not in v}

    def extract(self, image_path: str) -> dict:
        result = self.converter.convert(image_path)
        doc    = result.document
        rows, raw_tables = [], []

        for table in doc.tables:
            raw_tables.append(table)
            df = table.export_to_dataframe(doc=doc)
            if df is None or df.empty:
                continue
            df.columns  = [str(c).strip() for c in df.columns]
            simple_map  = self._map_simple_cols(df.columns.tolist())
            raw_map     = self._map_raw_cols(df.columns.tolist())
            for _, row in df.iterrows():
                entry = self._build_row(row, simple_map, raw_map)
                if any(v for k, v in entry.items()
                       if not k.startswith("_") and k != "a_emarge"):
                    rows.append(entry)

        return {"rows": rows, "tables": raw_tables, "doc": doc}

    def _map_simple_cols(self, cols: list[str]) -> dict:
        m = {}
        for f, spec in self._simple.items():
            for col in cols:
                if any(re.search(p, col.lower()) for p in spec["patterns"]):
                    m[f] = col; break
        return m

    def _map_raw_cols(self, cols: list[str]) -> dict:
        m = {}
        for rk, pats in _RAW_COL_PATTERNS.items():
            for col in cols:
                if any(re.search(p, col.lower()) for p in pats):
                    m[rk] = col; break
        return m

    def _build_row(self, row, simple_map: dict, raw_map: dict) -> dict:
        entry = {"a_emarge": "inconnu", "_sign_method": "—", "_bbox_emarge": None}
        for f, spec in self._simple.items():
            raw = self._cell(row, simple_map.get(f))
            tr  = spec.get("transform")
            entry[f] = tr(raw) if tr else raw
        raw_vals = {rk: self._cell(row, raw_map.get(rk)) for rk in _RAW_COL_PATTERNS}
        for f, spec in self._composed.items():
            args = [raw_vals.get(s, "") for s in spec["sources"]]
            tr   = spec.get("transform", lambda *v: " ".join(v).strip())
            entry[f] = tr(*args)
        if not entry.get("numero_ordre"):
            entry["numero_ordre"] = self._fallback_order(row)
        return entry

    def _cell(self, row, col: str | None) -> str:
        if not col or col not in row.index:
            return ""
        v = str(row[col]).strip()
        return "" if v.lower() in ("nan", "none", "-", "") else v

    def _fallback_order(self, row) -> str:
        candidates = []
        for col in row.index:
            v = str(row[col]).strip()
            if re.search(r"\d{2}[/\-]\d{2}[/\-]\d{4}", v):
                continue
            d = re.sub(r"\D", "", v)
            if 1 <= len(d) <= 6:
                candidates.append(d)
        return min(candidates, key=len).zfill(5) if candidates else ""

    def emargement_col_idx(self, df) -> int | None:
        pats = self.template.get("a_emarge", {}).get("patterns", [])
        for idx, col in enumerate(df.columns):
            if any(re.search(p, col.lower()) for p in pats):
                return idx
        return len(df.columns) - 1 if len(df.columns) >= 4 else None


# ══════════════════════════════════════════════════════════════════════════════
# CONVERTER DOCLING
# ══════════════════════════════════════════════════════════════════════════════

def build_docling_converter() -> "DocumentConverter":
    return DocumentConverter(
        format_options={
            InputFormat.IMAGE: ImageFormatOption(
                pipeline_options=PdfPipelineOptions(
                    do_ocr=True,
                    ocr_options=EasyOcrOptions(lang=["fr", "en"]),
                    do_table_structure=True,
                    table_structure_options=TableStructureOptions(
                        do_cell_matching=True,
                        mode=TableFormerMode.ACCURATE,
                    ),
                )
            )
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# OPENCV : CORRECTION D'ORIENTATION
# ══════════════════════════════════════════════════════════════════════════════

def correct_orientation_old(image_path: str) -> np.ndarray:
    pil = Image.open(image_path)
    try:
        exif = pil._getexif() or {}
        ang  = {3: 180, 6: 270, 8: 90}.get(exif.get(274, 1), 0)
        if ang:
            pil = pil.rotate(ang, expand=True)
    except Exception:
        pass
    return cv2.cvtColor(np.array(pil.convert("RGB")), cv2.COLOR_RGB2BGR)

def correct_orientation(image_path: str) -> np.ndarray:
    """
    Détecte et corrige l'orientation d'une photo de document.
    1. Lit les métadonnées EXIF pour la rotation
    2. Applique une détection de lignes Hough pour affiner l'angle
    """
    # Lecture avec Pillow pour respecter l'EXIF
    pil_img = Image.open(image_path)

    # Correction EXIF automatique
    exif_rotation = {3: 180, 6: 270, 8: 90}
    try:
        exif = pil_img._getexif() or {}
        orientation = exif.get(274, 1)  # tag 274 = Orientation
        angle = exif_rotation.get(orientation, 0)
        if angle:
            pil_img = pil_img.rotate(angle, expand=True)
    except Exception:
        pass

    img = np.array(pil_img.convert("RGB"))
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # Détection de l'angle de skew via les lignes horizontales
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                             minLineLength=50, maxLineGap=10)
    #lines, edges, gray = None, None, None
    if lines is not None:
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 != x1:
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                angles.append(angle)

        if angles:
            median_angle = float(np.median(angles))
            if abs(median_angle) > 0.5:  # seuil minimal pour éviter le bruit
                h, w = img_bgr.shape[:2]
                angle_rad = np.radians(median_angle)
                # Calcul des nouvelles dimensions pour contenir l'image tournée
                cos_a = abs(np.cos(angle_rad))
                sin_a = abs(np.sin(angle_rad))
                new_w = int(w * cos_a + h * sin_a)
                new_h = int(w * sin_a + h * cos_a)
                M = cv2.getRotationMatrix2D((w / 2, h / 2), -median_angle, 1.0)
                # Ajuster la matrice pour centrer dans les nouvelles dimensions
                M[0, 2] += (new_w - w) / 2
                M[1, 2] += (new_h - h) / 2
                img_bgr = cv2.warpAffine(
                    img_bgr, M, (new_w, new_h),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=(255, 255, 255)
                )

    return img_bgr


def save_temp(img: np.ndarray, original: str) -> str:
    tmp = original + "_corrected.jpg"
    cv2.imwrite(tmp, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return tmp


# ══════════════════════════════════════════════════════════════════════════════
# OLLAMA
# ══════════════════════════════════════════════════════════════════════════════

def check_ollama(model: str) -> bool:
    try:
        r     = requests.get("http://localhost:11434/api/tags", timeout=3)
        avail = [m["name"] for m in r.json().get("models", [])]
        if not any(model in m for m in avail):
            print(f"  ⚠  Modèle '{model}' absent. Lancez : ollama pull {model}")
            print(f"     Disponibles : {avail}")
            return False
        return True
    except Exception:
        print("  ✖  Ollama inaccessible sur localhost:11434")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT EXCEL
# ══════════════════════════════════════════════════════════════════════════════

COL_WIDTHS  = [22, 24, 10, 30, 42, 32, 12, 18]
H_FILL  = PatternFill("solid", fgColor="1E3A5F")
H_FONT  = Font(bold=True, color="FFFFFF", size=11)
ODD     = PatternFill("solid", fgColor="F7F9FC")
EVEN    = PatternFill("solid", fgColor="FFFFFF")
S_YES   = PatternFill("solid", fgColor="D4EDDA")
S_NO    = PatternFill("solid", fgColor="F8F9FA")
S_UNK   = PatternFill("solid", fgColor="FFF3CD")


def export_excel(rows: list, output: str, bureau: str, n_img: int, model: str) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Émargements"
    ws.row_dimensions[1].height = 20

    for c, (_, lbl) in enumerate(OUTPUT_FIELDS, 1):
        cell = ws.cell(row=1, column=c, value=lbl)
        cell.font = H_FONT; cell.fill = H_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(OUTPUT_FIELDS))}1"

    for r_i, row in enumerate(rows, 2):
        base  = ODD if r_i % 2 else EVEN
        emarg = row.get("a_emarge", "inconnu").lower()
        for c_i, (fld, _) in enumerate(OUTPUT_FIELDS, 1):
            cell = ws.cell(row=r_i, column=c_i, value=row.get(fld, ""))
            cell.alignment = Alignment(vertical="center",
                                       wrap_text=(fld in ("adresse", "date_lieu_naissance")))
            cell.fill = (S_YES if fld == "a_emarge" and emarg == "oui" else
                         S_NO  if fld == "a_emarge" and emarg == "non" else
                         S_UNK if fld == "a_emarge" else base)

    for i, w in enumerate(COL_WIDTHS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws2     = wb.create_sheet("Résumé")
    signed  = sum(1 for r in rows if r.get("a_emarge") == "oui")
    unsign  = sum(1 for r in rows if r.get("a_emarge") == "non")
    unk     = len(rows) - signed - unsign
    by_cv   = sum(1 for r in rows if "cv"     in r.get("_sign_method", ""))
    by_vis  = sum(1 for r in rows if "vision" in r.get("_sign_method", ""))

    ws2.column_dimensions["A"].width = 38
    ws2.column_dimensions["B"].width = 26

    summary = [
        ("Bureau de vote",                       bureau),
        ("", ""),
        ("Total électeurs",                      len(rows)),
        ("Ont émargé",                           signed),
        ("N'ont pas émargé",                     unsign),
        ("Statut inconnu",                       unk),
        ("Taux de participation",  f"{round(signed/len(rows)*100)} %" if rows else "—"),
        ("", ""),
        ("Images analysées",                     n_img),
        ("Détections par OpenCV",                by_cv),
        ("Détections par vision (Ollama)",       by_vis),
        ("Modèle vision",                        model),
        ("Données transmises à une API externe", "Aucune — 100 % local"),
        ("Généré le", datetime.datetime.now().strftime("%d/%m/%Y %H:%M")),
    ]
    for r_i, (lbl, val) in enumerate(summary, 1):
        a = ws2.cell(row=r_i, column=1, value=lbl)
        b = ws2.cell(row=r_i, column=2, value=val)
        if lbl:
            a.font = Font(bold=True, size=11)
            b.alignment = Alignment(horizontal="right")
        if lbl == "Taux de participation":
            b.font = Font(bold=True, color="185A30", size=14)

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def process_folder(
    folder: str,
    output_path: str,
    model: str = DEFAULT_MODEL,
    skip_vision: bool = False,
    debug: bool = False,
) -> None:
    if not DOCLING_OK:
        sys.exit(1)

    fp = Path(folder)
    if not fp.is_dir():
        print(f"✖  Dossier introuvable : {folder}"); sys.exit(1)

    bureau = fp.name
    images = sorted([p for p in fp.iterdir()
                     if p.suffix.lower() in SUPPORTED_EXT and not p.name.startswith(".")])
    if not images:
        print(f"✖  Aucune image dans {folder}"); sys.exit(1)

    debug_dir = Path("./debug_crops") / bureau if debug else None

    print(f"\n{'═'*60}")
    print(f"  Bureau : {bureau}  |  Images : {len(images)}")
    print(f"  Vision : {'désactivée' if skip_vision else model}")
    print(f"  Debug  : {'oui → ' + str(debug_dir) if debug else 'non'}")
    print(f"  Sortie : {output_path}")
    print(f"{'═'*60}\n")

    ollama_ok  = (not skip_vision) and check_ollama(model)
    extractor  = DocumentExtractor(EXTRACTION_TEMPLATE, build_docling_converter())
    all_rows: list[dict] = []
    tmp_files: list[str] = []

    for i, img_path in enumerate(images, 1):
        print(f"  [{i}/{len(images)}] {img_path.name}")

        print("        → Orientation OpenCV…", end=" ", flush=True)
        img_bgr = correct_orientation(str(img_path))
        h, w    = img_bgr.shape[:2]
        tmp     = save_temp(img_bgr, str(img_path))
        tmp_files.append(tmp)
        print("✓")

        print("        → Extraction Docling…", end=" ", flush=True)
        try:
            ext    = extractor.extract(tmp)
            rows   = ext["rows"]
            tables = ext["tables"]
            doc    = ext["doc"]
            print(f"✓  ({len(rows)} lignes)")
        except Exception as e:
            print(f"✖  {e}"); continue

        # ── Détection signature ────────────────────────────────────────────
        print("        → Détection signatures…")
        row_offset = 0

        for table in tables:
            df = table.export_to_dataframe(doc=doc)
            if df is None or df.empty:
                continue

            em_idx    = extractor.emargement_col_idx(df)
            data_grid = table.data.grid[1:]  # skip header

            for local_idx, grid_row in enumerate(data_grid):
                global_idx = row_offset + local_idx
                if global_idx >= len(rows):
                    continue

                crop      = None
                dbg_path  = None

                # Tentative 1 : bbox de la cellule
                if em_idx is not None and em_idx < len(grid_row):
                    sig_cell = grid_row[em_idx]
                    crop     = crop_from_bbox(img_bgr, getattr(sig_cell, "bbox", None), w, h)

                # Tentative 2 : fallback par position dans la ligne
                if crop is None:
                    row_cell  = grid_row[0] if grid_row else None
                    row_bbox  = getattr(row_cell, "bbox", None) if row_cell else None
                    crop      = crop_from_row_position(img_bgr, row_bbox, w, h)

                if debug and crop is not None:
                    dbg_path = str(debug_dir / img_path.stem / f"row{global_idx:03d}.jpg")

                result = detect_signature(crop, model, ollama_ok, dbg_path)

                rows[global_idx]["a_emarge"]     = result.verdict
                rows[global_idx]["_sign_method"] = result.method

                sym = "✓" if result.verdict == "oui" else ("·" if result.verdict == "non" else "?")
                print(f"          ligne {local_idx+1:3d}: {result.verdict:7s} "
                      f"[{result.method:9s}  conf={result.confidence:.2f}] {sym}")

            row_offset += len(data_grid)

        for r in rows:
            r["_bureau"] = bureau
            r["_source"] = img_path.name

        all_rows.extend(rows)

    print(f"\n  → Export Excel ({len(all_rows)} électeurs)…", end=" ", flush=True)
    export_excel(all_rows, output_path, bureau, len(images), model if not skip_vision else "—")
    print("✓")

    for tmp in tmp_files:
        try: os.remove(tmp)
        except Exception: pass

    signed  = sum(1 for r in all_rows if r.get("a_emarge") == "oui")
    unsign  = sum(1 for r in all_rows if r.get("a_emarge") == "non")
    unknown = len(all_rows) - signed - unsign
    by_cv   = sum(1 for r in all_rows if "cv"     in r.get("_sign_method", ""))
    by_vis  = sum(1 for r in all_rows if "vision" in r.get("_sign_method", ""))

    print(f"\n{'═'*60}")
    print(f"  ✅ Terminé")
    print(f"  Électeurs        : {len(all_rows)}")
    print(f"  Ont émargé       : {signed}")
    print(f"  N'ont pas émargé : {unsign}  |  Inconnu : {unknown}")
    if all_rows:
        print(f"  Participation    : {round(signed/len(all_rows)*100)} %")
    print(f"  Détections CV    : {by_cv}  |  Vision : {by_vis}")
    print(f"  Fichier          : {output_path}")
    print(f"{'═'*60}\n")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRÉE
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extraction liste d'émargement — Docling + détection hybride CV/vision"
    )
    parser.add_argument("--dossier",     "-d", required=True)
    parser.add_argument("--sortie",      "-o", default=None)
    parser.add_argument("--modele",      "-m", default=DEFAULT_MODEL)
    parser.add_argument("--skip-vision", action="store_true",
                        help="Utiliser uniquement OpenCV (pas d'Ollama)")
    parser.add_argument("--debug",       action="store_true",
                        help="Sauvegarder les crops annotés dans ./debug_crops/")

    args   = parser.parse_args()
    output = args.sortie or f"./emargements_{Path(args.dossier).name}.xlsx"

    process_folder(
        folder=args.dossier,
        output_path=output,
        model=args.modele,
        skip_vision=args.skip_vision,
        debug=args.debug,
    )