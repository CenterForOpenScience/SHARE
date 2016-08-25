# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/xenial64"

  config.vm.provider "virtualbox" do |v|
    v.memory = 1024
  end

  config.vm.network "forwarded_port", guest: 8000, host: 8000

  config.vm.provision "shell",
    inline: <<SCRIPT
sudo apt-get update -y
sudo apt-get install -y git docker.io build-essential libffi-dev \
    python3.5 python3.5-dev virtualenv \
    libpq-dev libxml2-dev libxslt1-dev
virtualenv -p python3.5 ~/venv
. ~/venv/bin/activate
echo '. $HOME/venv/bin/activate' >>~/.bashrc
git clone https://github.com/CenterForOpenScience/SHARE.git
cd SHARE
pip install -r requirements.txt
pip install docker-compose
sudo $(which docker-compose) up -d rabbitmq postgres elasticsearch
./up.sh
SCRIPT
end
