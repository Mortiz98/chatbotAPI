# Frontend del ChatBot RAG

## Estructura
```
frontend/
├── index.html      # Interfaz principal
├── styles.css      # Estilos
└── app.js          # Lógica de la aplicación
```

## Cómo usar

### Opción 1: Live Server (VS Code) - Recomendado
1. Instala la extensión "Live Server" en VS Code
2. Abre `frontend/index.html`
3. Click derecho → "Open with Live Server"
4. Se abrirá en `http://localhost:5500`

### Opción 2: Python HTTP Server
```bash
cd frontend
python -m http.server 5500
```
Luego abre: http://localhost:5500

### Opción 3: Node.js (npx serve)
```bash
cd frontend
npx serve -p 5500
```

## Funcionalidades

✅ Login / Registro  
✅ Chat con el bot RAG  
✅ Subir documentos PDF  
✅ Listar documentos indexados  
✅ Eliminar documentos  
✅ Nueva sesión de chat  

## Flujo de uso

1. Regístrate o inicia sesión
2. Sube uno o más PDFs desde el panel lateral
3. Espera que se indexen (aparecerá mensaje de éxito)
4. Escribe preguntas en el chat sobre el contenido de los documentos
5. El bot responderá basándose SOLO en los documentos subidos

## Notas

- El frontend se conecta a `http://localhost:8000` (backend FastAPI)
- Asegúrate de que el backend esté corriendo antes de usar el frontend
- Las cookies se manejan automáticamente para autenticación