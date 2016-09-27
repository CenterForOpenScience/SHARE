# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-16.04"

  config.vm.provider "virtualbox" do |v|
    v.memory = 1024
  end

  config.vm.network "forwarded_port", guest: 8000, host: 8000

  config.vm.provision "shell",
    privileged: false,
    inline: <<SCRIPT
sudo apt-get update -y
sudo apt-get install -y docker.io build-essential libffi-dev \
    python3.5 python3.5-dev virtualenv \
    libpq-dev libxml2-dev libxslt1-dev
rm -rf ~/venv
virtualenv -p python3.5 ~/venv
. ~/venv/bin/activate
echo '. $HOME/venv/bin/activate' >>~/.bashrc
cd /vagrant
pip install -r requirements.txt
pip install docker-compose
sudo $(which docker-compose) up -d rabbitmq postgres elasticsearch
./up.sh
SCRIPT
end
