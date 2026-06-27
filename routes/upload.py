from fastapi import APIRouter, UploadFile, File, Header, HTTPException
from services.auth_service import decode_token
from services.storage_service import upload_file

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("/")
async def upload(file: UploadFile = File(...), authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    contents = await file.read()
    url = upload_file(contents, file.filename, file.content_type)
    return {"url": url, "filename": file.filename}
