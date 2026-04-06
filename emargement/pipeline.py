"""
Pipeline d'extraction de listes d'émargement
=============================================
Étape 1 — OpenCV    : correction d'orientation de l'image
Étape 2 — Docling   : OCR + extraction du tableau structuré + bounding boxes
Étape 3 — Vision    : détection de signature par cellule (via Ollama local)
Étape 4 — Export    : fichier Excel (.xlsx) avec openpyxl

Prérequis
---------
pip install -r requirements.txt

Ollama (https://ollama.com) doit être installé et lancé localement.
Modèle vision recommandé (léger) :
  ollama pull moondream          # 1.8 B — très rapide, idéal CPU
  ollama pull qwen2-vl:2b        # 2 B   — meilleure précision
  ollama pull llava:7b           # 7 B   — si vous avez un GPU

Usage
-----
python pipeline.py --dossier /chemin/vers/bureau_001
python pipeline.py --dossier /chemin/vers/bureau_001 --modele qwen2-vl:2b
python pipeline.py --dossier /chemin/vers/bureau_001 --sortie /data/export.xlsx
"""

import argparse
import base64
import io
import json
import os
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# ── Docling ────────────────────────────────────────────────────────────────
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions, TableStructureOptions, TableFormerMode
    from docling.document_converter import PdfFormatOption, ImageFormatOption
    DOCLING_OK = True
except ImportError:
    print("⚠  Docling non installé. Lancez : pip install docling")
    DOCLING_OK = False

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

OLLAMA_URL   = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "moondream"           # ollama pull moondream
SIGNATURE_PROMPT = (
    "Look carefully at this small image. "
    "Is there a handwritten signature, initials, or any handwritten mark in it? "
    "Answer ONLY with one word: yes or no."
)
SUPPORTED_EXT = {".jpg", ".jpeg", ".png"}


# ══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 1 — PRÉ-TRAITEMENT OPENCV
# ══════════════════════════════════════════════════════════════════════════════

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
    #gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    #edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    #lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
    #                         minLineLength=50, maxLineGap=10)
    lines, edges, gray = None, None, None
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


def save_temp(img_bgr: np.ndarray, path: str) -> str:
    """Sauvegarde l'image corrigée dans un fichier temporaire."""
    tmp_path = path + "_corrected.jpg"
    cv2.imwrite(tmp_path, img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return tmp_path


# ══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 2 — EXTRACTION DOCLING
# ══════════════════════════════════════════════════════════════════════════════

def build_converter() -> "DocumentConverter":
    """Construit le convertisseur Docling optimisé pour les images."""
    ocr_options = EasyOcrOptions(lang=["fr", "en"])
    table_options = TableStructureOptions(
        do_cell_matching=True,
        mode=TableFormerMode.ACCURATE
        )
    converter = DocumentConverter(
        format_options={
            InputFormat.IMAGE: ImageFormatOption(
                pipeline_options=PdfPipelineOptions(
                    do_ocr=True,
                    ocr_options=ocr_options,
                    do_table_structure=True,
                    table_structure_options=table_options,
                )
            )
        }
    )
    return converter


def extract_with_docling(converter: "DocumentConverter", image_path: str) -> dict:
    """
    Retourne un dict contenant :
    - rows   : liste de dicts {numero_ordre, nom, prenom, adresse,
                               date_naissance, lieu_naissance}
    - tables : objets tableau bruts Docling (pour les bounding boxes)
    - doc    : document Docling complet
    """
    result = converter.convert(image_path)
    doc = result.document

    rows = []
    raw_tables = []

    for table in doc.tables:
        raw_tables.append(table)
        df = table.export_to_dataframe(doc=doc)
        if df is None or df.empty:
            continue

        df.columns = [str(c).strip() for c in df.columns]

        # Tentative de mapping automatique des colonnes
        col_map = _map_columns(df.columns.tolist())

        for _, row in df.iterrows():
            entry = {
                "numero_ordre":   _get(row, col_map, "numero_ordre"),
                "nom":            _get(row, col_map, "nom"),
                "prenom":         _get(row, col_map, "prenom"),
                "adresse":        _get(row, col_map, "adresse"),
                "date_naissance": _get(row, col_map, "date_naissance"),
                "lieu_naissance": _get(row, col_map, "lieu_naissance"),
                "a_emarge":       "inconnu",  # sera rempli par le modèle vision
                "_bbox_row":      None,       # bbox de la ligne pour le crop
            }
            # Ignorer les lignes complètement vides
            meaningful = [v for k, v in entry.items()
                          if k not in ("a_emarge", "_bbox_row") and v]
            if meaningful:
                rows.append(entry)

    return {"rows": rows, "tables": raw_tables, "doc": doc}


def _map_columns(cols: list) -> dict:
    """Mappe les colonnes détectées vers nos clés internes."""
    mapping = {
        "numero_ordre":   [r"n[°o]", r"ordre", r"numéro"],
        "nom":            [r"\bnom\b", r"patronyme"],
        "prenom":         [r"prénom", r"prenom"],
        "adresse":        [r"adresse", r"rattachement", r"domicile"],
        "date_naissance": [r"date", r"naissance", r"né\b", r"nés"],
        "lieu_naissance": [r"lieu", r"commune", r"ville"],
    }
    result = {}
    for key, patterns in mapping.items():
        for col in cols:
            col_lower = col.lower()
            for pat in patterns:
                if re.search(pat, col_lower):
                    result[key] = col
                    break
            if key in result:
                break
    return result


def _get(row, col_map: dict, key: str) -> str:
    col = col_map.get(key)
    if col and col in row.index:
        val = str(row[col]).strip()
        return "" if val.lower() in ("nan", "none", "-") else val
    return ""


# ══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 3 — DÉTECTION DE SIGNATURE (MODÈLE VISION LOCAL)
# ══════════════════════════════════════════════════════════════════════════════

def crop_signature_cell(img_bgr: np.ndarray, bbox, img_width: int, img_height: int) -> np.ndarray | None:
    """
    Découpe la cellule d'émargement dans l'image originale
    à partir de la bounding box Docling.
    bbox : objet BoundingBox Docling (coordonnées normalisées 0..1)
    """
    try:
        x0 = int(bbox.l * img_width)
        y0 = int(bbox.t * img_height)
        x1 = int(bbox.r * img_width)
        y1 = int(bbox.b * img_height)

        # Marge de sécurité
        pad = 4
        x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
        x1, y1 = min(img_width, x1 + pad), min(img_height, y1 + pad)

        if (x1 - x0) < 10 or (y1 - y0) < 10:
            return None

        return img_bgr[y0:y1, x0:x1]
    except Exception:
        return None


def image_to_base64(img_bgr: np.ndarray) -> str:
    """Encode un array OpenCV en base64 JPEG."""
    _, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def ask_vision_model(img_bgr: np.ndarray, model: str) -> str:
    """
    Envoie une cellule (crop) au modèle vision Ollama.
    Retourne "oui", "non" ou "inconnu".
    """
    b64 = image_to_base64(img_bgr)
    payload = {
        "model":  model,
        "prompt": SIGNATURE_PROMPT,
        "images": [b64],
        "stream": False,
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        text = resp.json().get("response", "").strip().lower()
        if text.startswith("yes") or "yes" in text[:20]:
            return "oui"
        if text.startswith("no") or "no" in text[:20]:
            return "non"
        return "inconnu"
    except requests.exceptions.ConnectionError:
        print("  ⚠  Ollama non disponible. Lancez : ollama serve")
        return "inconnu"
    except Exception as e:
        print(f"  ⚠  Erreur vision model: {e}")
        return "inconnu"


def check_ollama(model: str) -> bool:
    """Vérifie qu'Ollama est lancé et que le modèle est disponible."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        if not any(model in m for m in models):
            print(f"  ⚠  Modèle '{model}' non trouvé. Lancez : ollama pull {model}")
            print(f"     Modèles disponibles : {models}")
            return False
        return True
    except Exception:
        print("  ✖  Impossible de joindre Ollama sur localhost:11434")
        print("     Assurez-vous qu'Ollama est installé et lancé (ollama serve)")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 4 — EXPORT EXCEL
# ══════════════════════════════════════════════════════════════════════════════

HEADER = [
    "Bureau de vote", "Fichier source", "N° ordre",
    "Nom", "Prénom", "Adresse",
    "Date de naissance", "Lieu de naissance", "A émargé"
]

COL_WIDTHS = [22, 24, 10, 22, 18, 42, 16, 22, 12]

HEADER_FILL  = PatternFill("solid", fgColor="1E3A5F")
HEADER_FONT  = Font(bold=True, color="FFFFFF", size=11)
HEADER_ALIGN = Alignment(horizontal="center", vertical="center")

ODD_FILL  = PatternFill("solid", fgColor="F7F9FC")
EVEN_FILL = PatternFill("solid", fgColor="FFFFFF")

SIGN_YES_FILL = PatternFill("solid", fgColor="D4EDDA")
SIGN_NO_FILL  = PatternFill("solid", fgColor="F8F9FA")
SIGN_UNK_FILL = PatternFill("solid", fgColor="FFF3CD")


def export_excel(all_rows: list, output_path: str, bureau: str, n_images: int) -> None:
    wb = Workbook()

    # ── Feuille principale ───────────────────────────────────────────────────
    ws = wb.active
    ws.title = "Émargements"
    ws.row_dimensions[1].height = 20

    for c_idx, header in enumerate(HEADER, 1):
        cell = ws.cell(row=1, column=c_idx, value=header)
        cell.font  = HEADER_FONT
        cell.fill  = HEADER_FILL
        cell.alignment = HEADER_ALIGN

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(HEADER))}1"

    for r_idx, row in enumerate(all_rows, 2):
        data = [
            row.get("_bureau", ""),
            row.get("_source", ""),
            row.get("numero_ordre", ""),
            row.get("nom", ""),
            row.get("prenom", ""),
            row.get("adresse", ""),
            row.get("date_naissance", ""),
            row.get("lieu_naissance", ""),
            row.get("a_emarge", "inconnu"),
        ]
        fill = ODD_FILL if r_idx % 2 else EVEN_FILL
        emarge = data[-1].lower()

        for c_idx, value in enumerate(data, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            cell.alignment = Alignment(vertical="center", wrap_text=(c_idx == 6))
            if c_idx == len(HEADER):  # colonne "A émargé"
                if emarge == "oui":
                    cell.fill = SIGN_YES_FILL
                elif emarge == "non":
                    cell.fill = SIGN_NO_FILL
                else:
                    cell.fill = SIGN_UNK_FILL
            else:
                cell.fill = fill

    for i, width in enumerate(COL_WIDTHS, 1):
        ws.column_dimensions[get_column_letter(i)].width = width

    # ── Feuille résumé ───────────────────────────────────────────────────────
    ws2 = wb.create_sheet("Résumé")
    signed   = sum(1 for r in all_rows if r.get("a_emarge", "").lower() == "oui")
    unsigned = sum(1 for r in all_rows if r.get("a_emarge", "").lower() == "non")
    unknown  = len(all_rows) - signed - unsigned
    rate     = f"{round(signed / len(all_rows) * 100)}%" if all_rows else "—"

    summary_data = [
        ("Bureau de vote",         bureau),
        ("", ""),
        ("Total électeurs",        len(all_rows)),
        ("Ont émargé",             signed),
        ("N'ont pas émargé",       unsigned),
        ("Statut inconnu",         unknown),
        ("Taux de participation",  rate),
        ("", ""),
        ("Images analysées",       n_images),
        ("Modèle OCR",             "Docling"),
        ("Modèle vision",          "Ollama (local)"),
        ("Données transmises à une API externe", "Aucune"),
        ("Généré le", __import__("datetime").datetime.now().strftime("%d/%m/%Y %H:%M")),
    ]

    ws2.column_dimensions["A"].width = 32
    ws2.column_dimensions["B"].width = 24

    for r_idx, (label, value) in enumerate(summary_data, 1):
        a = ws2.cell(row=r_idx, column=1, value=label)
        b = ws2.cell(row=r_idx, column=2, value=value)
        if label:
            a.font = Font(bold=True, size=11)
            b.alignment = Alignment(horizontal="right")
        if label == "Taux de participation":
            b.font = Font(bold=True, color="185A30", size=14)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def process_folder(
    folder: str,
    output_path: str,
    model: str = DEFAULT_MODEL,
    skip_vision: bool = False,
) -> None:
    folder_path = Path(folder)
    if not folder_path.is_dir():
        print(f"✖  Dossier introuvable : {folder}")
        sys.exit(1)

    bureau = folder_path.name
    images = sorted([
        p for p in folder_path.iterdir()
        if p.suffix.lower() in SUPPORTED_EXT and not p.name.startswith(".")
    ])

    if not images:
        print(f"✖  Aucune image ({', '.join(SUPPORTED_EXT)}) dans {folder}")
        sys.exit(1)

    print(f"\n{'═'*60}")
    print(f"  Bureau de vote : {bureau}")
    print(f"  Images trouvées : {len(images)}")
    print(f"  Modèle vision  : {'désactivé (--skip-vision)' if skip_vision else model}")
    print(f"  Sortie         : {output_path}")
    print(f"{'═'*60}\n")

    if not DOCLING_OK:
        sys.exit(1)

    # Vérifie Ollama (sauf si vision désactivée)
    ollama_ok = skip_vision or check_ollama(model)

    converter = build_converter()
    all_rows  = []
    tmp_files = []

    for i, img_path in enumerate(images, 1):
        print(f"  [{i}/{len(images)}] {img_path.name}")

        # ── Étape 1 : correction orientation ──────────────────────────────
        print("        → Correction orientation (OpenCV)…", end=" ")
        img_bgr = correct_orientation(str(img_path))
        h, w    = img_bgr.shape[:2]
        tmp     = save_temp(img_bgr, str(img_path))
        tmp_files.append(tmp)
        print("✓")
        #input(f"        (aperçu corrigé sauvegardé : {tmp}) [appuyez sur Entrée pour continuer]")
        #continue

        # ── Étape 2 : OCR Docling ──────────────────────────────────────────
        print("        → Extraction Docling…", end=" ")
        try:
            extracted = extract_with_docling(converter, tmp)
            rows      = extracted["rows"]
            tables    = extracted["tables"]
            print(f"✓  ({len(rows)} lignes détectées)")
        except Exception as e:
            print(f"✖  {e}")
            continue

        # ── Étape 3 : détection signature ─────────────────────────────────
        if ollama_ok and not skip_vision and tables:
            print(f"        → Détection signatures ({model})…")

            # Identifier la colonne d'émargement dans chaque tableau
            for table_idx, table in enumerate(tables):
                df = table.export_to_dataframe(doc=extracted["doc"])
                if df is None or df.empty:
                    continue

                emargement_col_idx = _find_emargement_col(df)
                if emargement_col_idx is None:
                    print("          (colonne émargement non trouvée, skip vision)")
                    continue

                # Itérer sur les cellules de la colonne signature
                try:
                    for row_idx, cell in enumerate(
                        table.data.grid[1:]  # skip header row
                    ):
                        if emargement_col_idx >= len(cell):
                            continue
                        sig_cell = cell[emargement_col_idx]

                        if sig_cell.bbox is None:
                            continue

                        crop = crop_signature_cell(img_bgr, sig_cell.bbox, w, h)
                        if crop is None:
                            continue

                        result = ask_vision_model(crop, model)

                        # Associer au bon électeur
                        global_row_idx = sum(
                            len(extract_with_docling(converter, tmp)["rows"])
                            for _ in range(table_idx)  # offset tables précédents
                        ) + row_idx

                        if global_row_idx < len(rows):
                            rows[global_row_idx]["a_emarge"] = result
                            symbol = "✓" if result == "oui" else "·"
                            print(f"          ligne {row_idx+1}: {result} {symbol}")
                except Exception as e:
                    print(f"          ⚠  Erreur accès bbox: {e}")
                    print("          (fallback: émargement = inconnu)")

        # Ajouter la source
        for r in rows:
            r["_bureau"] = bureau
            r["_source"] = img_path.name
            r["nom"]     = r["nom"].upper()

        all_rows.extend(rows)

    # ── Étape 4 : export Excel ─────────────────────────────────────────────
    print(f"\n  → Export Excel ({len(all_rows)} électeurs)…", end=" ")
    export_excel(all_rows, output_path, bureau, len(images))
    print("✓")

    # Nettoyage fichiers temporaires
    for tmp in tmp_files:
        try:
            os.remove(tmp)
        except Exception:
            pass

    # Résumé
    signed   = sum(1 for r in all_rows if r.get("a_emarge") == "oui")
    unsigned = sum(1 for r in all_rows if r.get("a_emarge") == "non")
    unknown  = len(all_rows) - signed - unsigned

    print(f"\n{'═'*60}")
    print(f"  ✅ Terminé")
    print(f"  Électeurs extraits : {len(all_rows)}")
    print(f"  Ont émargé         : {signed}")
    print(f"  N'ont pas émargé   : {unsigned}")
    print(f"  Statut inconnu     : {unknown}")
    if all_rows:
        print(f"  Participation      : {round(signed / len(all_rows) * 100)}%")
    print(f"  Fichier généré     : {output_path}")
    print(f"{'═'*60}\n")


def _find_emargement_col(df) -> int | None:
    """Cherche la colonne d'émargement (signature) dans le tableau."""
    patterns = [r"émarg", r"emarg", r"signature", r"sign\.", r"paraph"]
    for idx, col in enumerate(df.columns):
        col_lower = str(col).lower()
        for pat in patterns:
            if re.search(pat, col_lower):
                return idx
    # Heuristique : dernière colonne (souvent la signature)
    if len(df.columns) > 3:
        return len(df.columns) - 1
    return None


# ══════════════════════════════════════════════════════════════════════════════
# ENTRÉE
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extraction liste d'émargement — Docling + vision locale"
    )
    parser.add_argument(
        "--dossier", "-d", required=True,
        help="Chemin vers le dossier du bureau de vote (contient les images)"
    )
    parser.add_argument(
        "--sortie", "-o", default=None,
        help="Chemin du fichier Excel de sortie (défaut : ./emargements_<bureau>.xlsx)"
    )
    parser.add_argument(
        "--modele", "-m", default=DEFAULT_MODEL,
        help=f"Modèle Ollama pour la vision (défaut : {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--skip-vision", action="store_true",
        help="Désactiver la détection de signature (OCR seul)"
    )

    args = parser.parse_args()

    bureau_name = Path(args.dossier).name
    output = args.sortie or f"./emargements_{bureau_name}.xlsx"

    process_folder(
        folder      = args.dossier,
        output_path = output,
        model       = args.modele,
        skip_vision = args.skip_vision,
    )
