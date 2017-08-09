#!/bin/bash
clear
echo "Thank you for wanting to install Untangled 2017."
echo "The installation is just under 25 megabytes."

clear
echo "Part 1 of 2."
git clone https://github.com/neontribe/untangled-2017.git
clear
echo "Part 2 of 2."
cd untangled-2017
sh install.sh
clear
echo "The installation has finished."
echo "Have fun!"