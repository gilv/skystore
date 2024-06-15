/usr/bin/curl https://sh.rustup.rs -sSf | /bin/sh -s -- -y
. "$HOME/.cargo/env"
cargo install just --force
git clone https://github.com/gilv/skystore
cd skystore
git checkout listen-all
cd s3-proxy
cargo build
cd ../store-server
pip install -r requirements.txt
cd ..
pip install -U .

