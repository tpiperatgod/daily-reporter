#!/bin/bash
# Complete verification workflow for Ollama embedding provider implementation

set -e  # Exit on error

echo "================================================================================"
echo "Ollama Embedding Provider - Complete Verification Workflow"
echo "================================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check Ollama installation
echo -e "${YELLOW}Step 1: Checking Ollama installation...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✅ Ollama is installed${NC}"
    ollama --version
else
    echo -e "${RED}❌ Ollama not found. Install with: brew install ollama${NC}"
    exit 1
fi
echo ""

# Step 2: Check Ollama service
echo -e "${YELLOW}Step 2: Checking Ollama service...${NC}"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama service is running${NC}"
else
    echo -e "${RED}❌ Ollama service not running. Start with: ollama serve${NC}"
    exit 1
fi
echo ""

# Step 3: Check model availability
echo -e "${YELLOW}Step 3: Checking bge-m3:567m model...${NC}"
if ollama list | grep -q "bge-m3:567m"; then
    echo -e "${GREEN}✅ Model bge-m3:567m is available${NC}"
    ollama list | grep bge-m3
else
    echo -e "${YELLOW}⚠️  Model not found. Pulling bge-m3:567m...${NC}"
    ollama pull bge-m3:567m
    echo -e "${GREEN}✅ Model pulled successfully${NC}"
fi
echo ""

# Step 4: Test Python imports
echo -e "${YELLOW}Step 4: Testing Python imports...${NC}"
python3 -c "
from app.services.embedding.factory import get_embedding_provider
from app.services.embedding.ollama_provider import OllamaEmbeddingProvider
from app.services.llm.client import LLMClient
print('✅ All imports successful')
" 2>&1
echo ""

# Step 5: Run Ollama provider test
echo -e "${YELLOW}Step 5: Running Ollama provider test...${NC}"
LLM_EMBEDDING_PROVIDER=ollama python3 demos/test_ollama_embedding.py
echo ""

# Step 6: Run integration verification
echo -e "${YELLOW}Step 6: Running end-to-end integration test...${NC}"
python3 demos/verify_integration.py
echo ""

# Step 7: Summary
echo "================================================================================"
echo -e "${GREEN}✅ All verification steps completed successfully!${NC}"
echo "================================================================================"
echo ""
echo "System Status:"
echo "  ✅ Ollama service running"
echo "  ✅ Model bge-m3:567m available"
echo "  ✅ Python dependencies working"
echo "  ✅ Provider tests passing"
echo "  ✅ Integration tests passing"
echo ""
echo "Next Steps:"
echo "  1. Update .env with: LLM_EMBEDDING_PROVIDER=ollama"
echo "  2. Restart Celery worker"
echo "  3. Run collect_data task"
echo "  4. Verify embedding_hash in database"
echo ""
echo "To switch back to OpenAI provider:"
echo "  Set LLM_EMBEDDING_PROVIDER=openai in .env"
echo ""
echo "================================================================================"
