echo "accumulater.sh"
cd /Users/yuji.kanamitsu/Documents/BATMAN

/Users/yuji.kanamitsu/.pyenv/shims/python3 ./src/accumulater.py

# 0 11,14,17 * * * /Users/yuji.kanamitsu/Documents/BATMAN/shell/accumulater.sh > /Users/yuji.kanamitsu/Documents/BATMAN/system-log/cron.log 2>&1