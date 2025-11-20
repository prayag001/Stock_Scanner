#!/bin/bash
# Quick deploy to Oracle Cloud VM

VM_IP="your-vm-ip"
VM_USER="opc"
LOCAL_DIR="/c/Sandbox/VSCode_Projects/Stock_Bot"
REMOTE_DIR="/home/opc/Stock_Scanner"

echo "Deploying to Oracle Cloud VM..."

# Option A: Git push & pull (uncomment if using git)
# git add .
# git commit -m "Quick update"
# git push origin main
# ssh $VM_USER@$VM_IP "cd $REMOTE_DIR && git pull origin main"

# Option B: Direct file copy (faster for quick changes)
scp -r $LOCAL_DIR/src/* $VM_USER@$VM_IP:$REMOTE_DIR/src/
scp $LOCAL_DIR/.env $VM_USER@$VM_IP:$REMOTE_DIR/.env

# Restart bot (using venv if available, fallback to system python)
ssh $VM_USER@$VM_IP << 'EOF'
pkill -f 'python.*main.py'
cd /home/opc/Stock_Scanner
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Using virtual environment"
else
    echo "Using system Python"
fi
cd src
nohup python main.py > ../bot.log 2>&1 &
echo "Bot PID: $!"
EOF

echo "✅ Deployed! Bot restarted."
