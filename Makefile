# ------------------------------------------------------------------------------
# Color definitions
# ------------------------------------------------------------------------------
RED    := \033[0;31m
GREEN  := \033[0;32m
YELLOW := \033[0;33m
BLUE   := \033[0;34m
BOLD   := \033[1m
RESET  := \033[0m

# ------------------------------------------------------------------------------
# Help content
# ------------------------------------------------------------------------------
define HELP
$(BOLD)Manage ml-project-template Usage:$(RESET)

  $(GREEN)make clean$(RESET)        Clean Python compiled bytecode files.
  $(GREEN)make local$(RESET)        Deploy local infrastructure.
  $(GREEN)make deploy$(RESET)   	Deploy on genezio cloud.
  $(GREEN)make all$(RESET)          Show help.
endef

export HELP

# ------------------------------------------------------------------------------
# Targets
# ------------------------------------------------------------------------------
help:
	@echo "$$HELP"

local:
	genezio local

deploy:
	genezio deploy

clean:
	@echo "Cleaning up..."
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	@echo "Finished cleaning."

all: help

.PHONY: help clean local deploy