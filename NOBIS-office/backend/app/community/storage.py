import io,os,uuid,warnings
from pathlib import Path
from PIL import Image,ImageOps,UnidentifiedImageError
MAX_BYTES=5*1024*1024
Image.MAX_IMAGE_PIXELS=16_777_216

def validate_image(data):
 from .service import CommunityError
 if not data or len(data)>MAX_BYTES:raise CommunityError('이미지는 5MB 이하로 업로드해 주세요.',413)
 try:
  with warnings.catch_warnings():
   warnings.simplefilter('error',Image.DecompressionBombWarning)
   with Image.open(io.BytesIO(data),formats=['JPEG','PNG','WEBP']) as im:
    fmt=im.format
    if im.width>4096 or im.height>4096 or im.width*im.height>16_777_216 or getattr(im,'n_frames',1)!=1:raise ValueError('image limits')
    im.verify()
   with Image.open(io.BytesIO(data),formats=['JPEG','PNG','WEBP']) as im:
    im.load();im=ImageOps.exif_transpose(im);im=im.convert('RGBA' if 'A' in im.getbands() and fmt!='JPEG' else 'RGB');im.info.clear();buffer=io.BytesIO();im.save(buffer,format=fmt);clean=buffer.getvalue();width,height=im.size
   if len(clean)>MAX_BYTES:raise ValueError('encoded image too large')
   return clean,{'JPEG':'image/jpeg','PNG':'image/png','WEBP':'image/webp'}[fmt],width,height
 except (UnidentifiedImageError,OSError,ValueError,SyntaxError,Image.DecompressionBombError,Image.DecompressionBombWarning):raise CommunityError('JPG·PNG·WebP 정지 이미지만 허용하며 최대 4096×4096입니다.')

class LocalMediaStore:
 """Private blob boundary. A future object store implements put/path/delete with authorized proxy reads."""
 def __init__(self,root):self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
 def path(self,key):
  from .service import CommunityError
  if not key or Path(key).name!=key:raise CommunityError('이미지를 찾을 수 없습니다.',404)
  p=self.root/key
  if not p.is_file():raise CommunityError('이미지를 찾을 수 없습니다.',404)
  return p
 def put(self,data,kind):
  key=uuid.uuid4().hex+{'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}[kind];p=self.root/key
  fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
  with os.fdopen(fd,'wb') as stream:stream.write(data)
  return key
 def delete(self,key):
  if key and Path(key).name==key:(self.root/key).unlink(missing_ok=True)
