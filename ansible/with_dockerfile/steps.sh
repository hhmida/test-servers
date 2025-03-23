ssh-keygen -f keycontainer
docker build -t ubuntu-lab .
docker run -d -p 2022:22 ubuntu-lab
cp containerkey ~/.ssh/
ssh hhmida@localhost -p2022 -i ~/.ssh/containerkey

OR
simply add in your ssh config file like below so that from next time u can easily access container.

less ~/.ssh/config
Host localhost
        HostName localhost
        User thunder
        Port 2022
        IdentityFile ~/.ssh/keycontainer

AnsiblePermalink
I hope you have already installed ansible on your control host. If yes then first create an inventory file like below.

cat inventory.ini 
[local]
localhost
Now check ansible connection through AD-Hoc Command

ansible local -i inventory.ini -m ping       
localhost | SUCCESS => {
    "ansible_facts": {
        "discovered_interpreter_python": "/usr/bin/python3"
    },
    "changed": false,
    "ping": "pong"
}

ansible local -i inventory.ini -a 'hostname -I' 
localhost | CHANGED | rc=0 >>
172.17.0.2