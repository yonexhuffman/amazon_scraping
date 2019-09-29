#!/bin/sh

cd "$(dirname "$0")"
cd ..

mkdir -p build

cd build
git clone git@github.com:Danielchernokalov88/isbn_scrapy.git 

# 
echo yes | cp isbn_scrapy/abe/isbn/settings.prod.py isbn_scrapy/abe/isbn/settings.py 
echo yes | cp isbn_scrapy/ucbc/isbn/settings.prod.py isbn_scrapy/ucbc/isbn/settings.py 

rm isbn_scrapy/abe/isbn/settings.prod.py
rm isbn_scrapy/abe/isbn/settings.dev.py
rm isbn_scrapy/ucbc/isbn/settings.prod.py
rm isbn_scrapy/ucbc/isbn/settings.dev.py

# remove deploy script
rm isbn_scrapy/automation/deploy.sh

#
rm -rf isbn_scrapy/.git
# tar
tar czvf isbn_scrapy.tgz isbn_scrapy

readonly MY_PEM="/Users/xiong/Documents/projects/scrapping/server_info/xiaogangEC2.pem"
#

# deploy
scp -i "$MY_PEM" isbn_scrapy.tgz centos@3.218.171.135:~/
ssh -i "$MY_PEM" centos@3.218.171.135 'tar xzf isbn_scrapy.tgz;source venv/bin/activate;pwd;cd isbn_scrapy;automation/run_abe.sh;'



# create a tarball of a git repository using git archive
# git archive --format=tar.gz -o ./build/isbn.tar.gz master


cd ..
rm -rf build