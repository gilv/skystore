/usr/bin/curl https://sh.rustup.rs -sSf | /bin/sh -s -- -y --default-toolchain none
. "$HOME/.cargo/env"
# Locked good Rust version for building SkyStore components
rustup install 1.77.0
cargo install just --force --version 1.40.0 --locked
git clone https://github.com/gilv/skystore
cd skystore
git checkout custom
cd s3-proxy
cargo build
cd ../store-server
pip install -r requirements.txt
cd ..
pip install -U .

