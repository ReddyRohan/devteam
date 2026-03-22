#!/bin/bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$HOME/.npm-global/bin:$PATH"
eval "$(pyenv init -)"

LOG_DIR=~/devteam/logs
mkdir -p $LOG_DIR

# Start LiteLLM
GH_TOKEN=$(gh auth token 2>/dev/null)
if [ -z "$GH_TOKEN" ]; then
    echo "$(date) ERROR: gh auth token failed" >> $LOG_DIR/startup.log
    exit 1
fi
sed "s/GITHUB_WORK_TOKEN_PLACEHOLDER/$GH_TOKEN/g" ~/nanoclaw-laptop/litellm/config.yaml > /tmp/litellm-active.yaml
nohup litellm --config /tmp/litellm-active.yaml --port 4000 >> $LOG_DIR/litellm.log 2>&1 &
echo "$(date) LiteLLM started (PID=$!)" >> $LOG_DIR/startup.log

# Wait for LiteLLM
for i in $(seq 1 30); do
    sleep 1
    curl -s http://localhost:4000/health > /dev/null 2>&1 && break
done
echo "$(date) LiteLLM ready" >> $LOG_DIR/startup.log

cd ~/devteam/agents

# Start Oracle agent
nohup python3 oracle.py >> $LOG_DIR/oracle.log 2>&1 &
echo "$(date) Oracle started (PID=$!)" >> $LOG_DIR/startup.log

# Start Dev agent
nohup python3 dev.py >> $LOG_DIR/dev.log 2>&1 &
echo "$(date) Dev started (PID=$!)" >> $LOG_DIR/startup.log