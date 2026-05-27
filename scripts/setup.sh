#!/bin/bash
# Aphrodite-builder dependency checker and setup wizard
# Detects and configures required/optional tools

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

check_command() {
    if command -v "$1" &> /dev/null; then
        version=$("$1" --version 2>&1 | head -1)
        echo -e "  ${GREEN}[OK]${NC} $1: $version"
        return 0
    else
        echo -e "  ${RED}[MISSING]${NC} $1"
        return 1
    fi
}

check_python_module() {
    if python3 -c "import $1" 2>/dev/null; then
        version=$(python3 -c "import $1; print($1.__version__)" 2>/dev/null || echo "installed")
        echo -e "  ${GREEN}[OK]${NC} $1: $version"
        return 0
    else
        echo -e "  ${RED}[MISSING]${NC} $1"
        return 1
    fi
}

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Aphrodite-builder Environment Setup   ${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# === Python ===
echo -e "${YELLOW}[1/6] Python Runtime${NC}"
check_command python3
echo ""

# === Core dependencies ===
echo -e "${YELLOW}[2/6] Core Python Packages${NC}"
check_python_module numpy
check_python_module yaml
check_python_module dataclasses 2>/dev/null || echo -e "  ${GREEN}[OK]${NC} dataclasses (builtin)"
echo ""

# === Computational Chemistry ===
echo -e "${YELLOW}[3/6] Computational Chemistry Tools${NC}"
orca_found=false
xtb_found=false
multiwfn_found=false

if check_command orca; then
    orca_found=true
fi
if check_command xtb; then
    xtb_found=true
fi
if check_command Multiwfn; then
    multiwfn_found=true
fi

echo ""
echo -e "  ${CYAN}ORCA${NC}: Quantum chemistry engine (DFT/DLPNO-CCSD(T))"
echo -e "    Install: https://orcaforum.cec.mpg.de/"
echo -e "    Required for: screening_pipeline, precision_ladder, battery_analysis"
echo ""
echo -e "  ${CYAN}xtb (GFN-xTB)${NC}: Semi-empirical quick screening"
echo -e "    Install: conda install -c conda-forge xtb"
echo -e "    Required for: precision_ladder (tier-1 screening)"
echo ""
echo -e "  ${CYAN}Multiwfn${NC}: Wavefunction analysis"
echo -e "    Install: http://sobereva.com/multiwfn/"
echo -e "    Required for: advanced charge transfer analysis"
echo ""

# === Molecular Toolkit ===
echo -e "${YELLOW}[4/6] Molecular Toolkit${NC}"
check_python_module rdkit
echo -e "    Install: conda install -c conda-forge rdkit"
check_python_module openbabel || echo -e "    (optional) Install: conda install -c conda-forge openbabel"
echo ""

# === AI/ML ===
echo -e "${YELLOW}[5/6] AI/ML Packages${NC}"
check_python_module torch
echo -e "    Install: pip install torch  (for BatteryFold neural model)"
check_python_module anthropic
echo -e "    Install: pip install anthropic  (for Claude AI interface)"
check_python_module openai
echo -e "    Install: pip install openai  (for GLM/DeepSeek AI interface)"
echo ""

# === AI Configuration ===
echo -e "${YELLOW}[6/6] AI Configuration${NC}"
if [ -f "config/ai_config.json" ]; then
    echo -e "  ${GREEN}[OK]${NC} config/ai_config.json found"
    provider=$(python3 -c "import json; print(json.load(open('config/ai_config.json')).get('provider', 'unknown'))" 2>/dev/null)
    echo -e "    Provider: $provider"
else
    echo -e "  ${YELLOW}[NOT CONFIGURED]${NC} Run: python3 -m src.cli.main setup --ai"
fi
echo ""

# === Summary ===
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Setup Summary                        ${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo "  Quick install (conda):"
echo "    conda create -n aphrodite python=3.11"
echo "    conda activate aphrodite"
echo "    pip install numpy pyyaml anthropic openai"
echo "    conda install -c conda-forge rdkit xtb"
echo ""
echo "  ORCA: Download from https://orcaforum.cec.mpg.de/ (free academic license)"
echo "  Multiwfn: Download from http://sobereva.com/multiwfn/ (free)"
echo ""
echo "  Configure AI:"
echo "    python3 -m src.cli.main setup --ai"
echo ""
