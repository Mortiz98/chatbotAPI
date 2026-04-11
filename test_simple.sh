#!/bin/bash

# Script de prueba SIMPLIFICADO para el chatbot RAG
# Ejecuta paso a paso con verificaciones

BASE_URL="http://localhost:8000"
COOKIE_JAR="cookies.txt"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   🤖 TEST CHATBOT RAG${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verificar servicios
echo -e "${YELLOW}Verificando servicios...${NC}"
if ! curl -s http://localhost:8000/ > /dev/null; then
    echo -e "${RED}❌ FastAPI no está corriendo${NC}"
    echo "Ejecuta: source venv/bin/activate && uvicorn main:app --reload"
    exit 1
fi

if ! curl -s http://localhost:6333/healthz > /dev/null; then
    echo -e "${RED}❌ Qdrant no está corriendo${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Servicios OK${NC}"
echo ""

# Login
echo -e "${YELLOW}1. Login...${NC}"
rm -f $COOKIE_JAR

curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpassword123"}' \
  -c $COOKIE_JAR > /dev/null

if [ -f $COOKIE_JAR ]; then
    echo -e "${GREEN}✅ Login OK${NC}"
else
    echo -e "${YELLOW}Intentando registro...${NC}"
    curl -s -X POST "$BASE_URL/auth/register" \
      -H "Content-Type: application/json" \
      -d '{"email": "test@example.com", "username": "testuser", "password": "testpassword123"}' > /dev/null
    
    curl -s -X POST "$BASE_URL/auth/login" \
      -H "Content-Type: application/json" \
      -d '{"email": "test@example.com", "password": "testpassword123"}' \
      -c $COOKIE_JAR > /dev/null
    echo -e "${GREEN}✅ Registro y login OK${NC}"
fi
echo ""

# Verificar documentos
echo -e "${YELLOW}2. Verificando documentos...${NC}"
DOCS=$(curl -s "$BASE_URL/documents/list" -b $COOKIE_JAR)
TOTAL=$(echo $DOCS | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_documents',0))" 2>/dev/null || echo "0")

if [ "$TOTAL" -gt 0 ]; then
    echo -e "${GREEN}✅ Hay $TOTAL documentos indexados${NC}"
else
    echo -e "${YELLOW}⚠️  No hay documentos. Indexando...${NC}"
    
    PDF=$(find documents -name "*.pdf" | head -1)
    if [ -z "$PDF" ]; then
        echo -e "${RED}❌ No hay PDFs en la carpeta documents/${NC}"
        exit 1
    fi
    
    echo "   Archivo: $PDF"
    echo "   Indexando (esto puede tardar unos minutos)..."
    
    INDEX=$(curl -s -X POST "$BASE_URL/documents/ingest" \
      -b $COOKIE_JAR \
      -F "file=@$PDF")
    
    echo "   Respuesta: $INDEX"
fi
echo ""

# Crear sesión
echo -e "${YELLOW}3. Creando sesión de chat...${NC}"
SESSION=$(curl -s -X POST "$BASE_URL/chat/sessions" -b $COOKIE_JAR)
SESSION_ID=$(echo $SESSION | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id'))" 2>/dev/null)

echo -e "${GREEN}✅ Sesión ID: $SESSION_ID${NC}"
echo ""

# Pregunta
echo -e "${YELLOW}4. Enviando pregunta...${NC}"
echo "Pregunta: 'Resume el documento'"
echo ""

RESPONSE=$(curl -s -X POST "$BASE_URL/chat/ask" \
  -H "Content-Type: application/json" \
  -b $COOKIE_JAR \
  -d "{\"content\": \"Resume el documento\", \"session_id\": $SESSION_ID}")

echo -e "${GREEN}Respuesta:${NC}"
echo $RESPONSE | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('content','Error'))" 2>/dev/null || echo "$RESPONSE"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Test completado${NC}"
echo -e "${BLUE}========================================${NC}"

rm -f $COOKIE_JAR
