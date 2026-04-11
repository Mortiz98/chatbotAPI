#!/bin/bash

# Script de prueba completo para el chatbot RAG
# Este script asume que hay un documento PDF en la carpeta documents/

BASE_URL="http://localhost:8000"
COOKIE_JAR="cookies.txt"
DOCUMENTS_DIR="documents"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║      🤖 CHATBOT RAG - SCRIPT DE PRUEBA COMPLETO              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# ============================================
# PASO 0: Verificar servicios
# ============================================
echo -e "${YELLOW}🔍 Paso 0: Verificando servicios...${NC}"

# Verificar FastAPI
echo -n "  FastAPI (uvicorn)... "
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ NO ESTÁ CORRIENDO${NC}"
    echo ""
    echo "Para iniciar el servidor, ejecuta en otra terminal:"
    echo -e "${YELLOW}  source venv/bin/activate && uvicorn main:app --reload${NC}"
    exit 1
fi

# Verificar Qdrant
echo -n "  Qdrant... "
if curl -s http://localhost:6333/healthz > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ NO ESTÁ CORRIENDO${NC}"
    echo ""
    echo "Para iniciar Qdrant, ejecuta:"
    echo -e "${YELLOW}  docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant${NC}"
    exit 1
fi
echo ""

# Limpiar cookies anteriores
rm -f $COOKIE_JAR

# ============================================
# PASO 1: Login
# ============================================
echo -e "${YELLOW}🔐 Paso 1: Autenticación${NC}"
echo "Email: test@example.com"
echo "Password: testpassword123"
echo ""

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }' \
  -c $COOKIE_JAR)

if [ -f $COOKIE_JAR ] && grep -q "access_token" $COOKIE_JAR; then
    echo -e "${GREEN}✅ Login exitoso${NC}"
else
    echo -e "${YELLOW}⚠️  Login falló, intentando registro...${NC}"
    
    # Intentar registro
    REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
      -H "Content-Type: application/json" \
      -d '{
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123"
      }')
    
    # Reintentar login
    LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
      -H "Content-Type: application/json" \
      -d '{
        "email": "test@example.com",
        "password": "testpassword123"
      }' \
      -c $COOKIE_JAR)
    
    if [ -f $COOKIE_JAR ] && grep -q "access_token" $COOKIE_JAR; then
        echo -e "${GREEN}✅ Registro y login exitosos${NC}"
    else
        echo -e "${RED}❌ Error de autenticación${NC}"
        exit 1
    fi
fi
echo ""

# ============================================
# PASO 2: Verificar documentos indexados
# ============================================
echo -e "${YELLOW}📚 Paso 2: Verificando documentos indexados${NC}"

DOCS_RESPONSE=$(curl -s -X GET "$BASE_URL/documents/list" -b $COOKIE_JAR)
TOTAL_DOCS=$(echo $DOCS_RESPONSE | grep -o '"total_documents":[0-9]*' | cut -d: -f2 || echo "0")

if [ "$TOTAL_DOCS" -gt 0 ] 2>/dev/null; then
    echo -e "${GREEN}✅ Hay $TOTAL_DOCS documentos indexados${NC}"
    echo "Documentos:"
    echo $DOCS_RESPONSE | python3 -m json.tool 2>/dev/null || echo $DOCS_RESPONSE
else
    echo -e "${YELLOW}⚠️  No hay documentos indexados${NC}"
    
    # Buscar PDFs en la carpeta documents
    PDF_COUNT=$(find $DOCUMENTS_DIR -name "*.pdf" -type f 2>/dev/null | wc -l)
    
    if [ "$PDF_COUNT" -eq 0 ]; then
        echo -e "${RED}❌ No se encontraron PDFs en la carpeta '$DOCUMENTS_DIR/'${NC}"
        echo "Por favor, coloca un archivo PDF en la carpeta documents/"
        exit 1
    fi
    
    # Indexar el primer PDF encontrado
    FIRST_PDF=$(find $DOCUMENTS_DIR -name "*.pdf" -type f | head -1)
    echo -e "${YELLOW}📄 Indexando documento: $(basename $FIRST_PDF)${NC}"
    
    INDEX_RESPONSE=$(curl -s -X POST "$BASE_URL/documents/ingest" \
      -b $COOKIE_JAR \
      -F "file=@$FIRST_PDF")
    
    echo "Respuesta:"
    echo $INDEX_RESPONSE | python3 -m json.tool 2>/dev/null || echo $INDEX_RESPONSE
    
    # Verificar que se indexó
    if echo $INDEX_RESPONSE | grep -q "chunks_indexed"; then
        echo -e "${GREEN}✅ Documento indexado exitosamente${NC}"
    else
        echo -e "${RED}❌ Error al indexar documento${NC}"
        exit 1
    fi
fi
echo ""

# ============================================
# PASO 3: Crear sesión de chat
# ============================================
echo -e "${YELLOW}💬 Paso 3: Creando sesión de chat${NC}"

SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/chat/sessions" -b $COOKIE_JAR)
SESSION_ID=$(echo $SESSION_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ -n "$SESSION_ID" ]; then
    echo -e "${GREEN}✅ Sesión creada: ID $SESSION_ID${NC}"
else
    echo -e "${RED}❌ Error creando sesión${NC}"
    exit 1
fi
echo ""

# ============================================
# PASO 4: Hacer preguntas de prueba
# ============================================
echo -e "${YELLOW}❓ Paso 4: Haciendo preguntas al chatbot${NC}"
echo ""

# Array de preguntas de prueba
PREGUNTAS=(
    "Resume el contenido del documento"
    "¿Cuáles son los puntos principales?"
    "Explica la teoría de la evolución según el documento"
)

for PREGUNTA in "${PREGUNTAS[@]}"; do
    echo -e "${BLUE}─────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}Pregunta:${NC} $PREGUNTA"
    echo ""
    
    ASK_RESPONSE=$(curl -s -X POST "$BASE_URL/chat/ask" \
      -H "Content-Type: application/json" \
      -b $COOKIE_JAR \
      -d "{
        \"content\": \"$PREGUNTA\",
        \"session_id\": $SESSION_ID
      }")
    
    # Verificar si la respuesta es válida
    if echo $ASK_RESPONSE | grep -q '"content"'; then
        echo -e "${GREEN}Respuesta:${NC}"
        echo $ASK_RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('content', 'Sin contenido'))" 2>/dev/null || echo $ASK_RESPONSE
    else
        echo -e "${RED}Error en la respuesta:${NC}"
        echo $ASK_RESPONSE | python3 -m json.tool 2>/dev/null || echo $ASK_RESPONSE
    fi
    
    echo ""
done

# ============================================
# RESUMEN
# ============================================
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              ✅ PRUEBA COMPLETADA EXITOSAMENTE               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "${BLUE}Resumen:${NC}"
echo "  • Autenticación: ✅"
echo "  • Documentos: ✅"
echo "  • Sesión de chat: ID $SESSION_ID"
echo "  • Preguntas realizadas: ${#PREGUNTAS[@]}"
echo ""
echo -e "${YELLOW}Para hacer más preguntas, usa:${NC}"
echo "  curl -X POST '$BASE_URL/chat/ask' \\"
echo "    -b $COOKIE_JAR \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"content\": \"Tu pregunta\", \"session_id\": $SESSION_ID}'"
echo ""

# Limpiar
rm -f $COOKIE_JAR
