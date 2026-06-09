.PHONY: deploy status restart logs help

# Customize these for your setup
CERBO_HOST ?= root@venus
REMOTE_DIR ?= /data/cerbo-p1-bridge

deploy:
	CERBO_HOST=$(CERBO_HOST) REMOTE_DIR=$(REMOTE_DIR) ./scripts/deploy-to-cerbo.sh

status:
	ssh -o BatchMode=yes $(CERBO_HOST) "'$(REMOTE_DIR)/manage.sh' status; svstat /service/cerbo-p1-bridge 2>/dev/null || true"

restart:
	ssh -o BatchMode=yes $(CERBO_HOST) "'$(REMOTE_DIR)/manage.sh' restart"

logs:
	ssh -o BatchMode=yes $(CERBO_HOST) "tail -f /var/log/cerbo-p1-bridge/current"

help:
	@echo "Targets:"
	@echo "  deploy   Sync project to Cerbo and run manage.sh install"
	@echo "  status   Check service status on Cerbo"
	@echo "  restart  Restart service on Cerbo"
	@echo "  logs     Tail live service logs on Cerbo"
	@echo ""
	@echo "Overrides:"
	@echo "  CERBO_HOST=root@192.168.0.x make deploy"
	@echo "  REMOTE_DIR=/data/cerbo-p1-bridge make deploy"
