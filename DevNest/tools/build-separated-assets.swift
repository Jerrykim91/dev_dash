import Foundation
import ImageIO
import CoreGraphics
import UniformTypeIdentifiers
// Build runtime PNG strips, idle frames and portable GIFs from generated 2x2 sheets.
let root=URL(fileURLWithPath:CommandLine.arguments.count>1 ? CommandLine.arguments[1] : FileManager.default.currentDirectoryPath)
let inputs=root.appendingPathComponent("source-assets/separated-inputs")
let output=root.appendingPathComponent("frontend/assets/characters")
func read(_ path:URL)->CGImage {CGImageSourceCreateImageAtIndex(CGImageSourceCreateWithURL(path as CFURL,nil)!,0,nil)!}
func context(_ w:Int,_ h:Int)->CGContext {CGContext(data:nil,width:w,height:h,bitsPerComponent:8,bytesPerRow:0,space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue)!}
func save(_ image:CGImage,_ name:String){
 let dst=CGImageDestinationCreateWithURL(output.appendingPathComponent(name) as CFURL,UTType.png.identifier as CFString,1,nil)!
 CGImageDestinationAddImage(dst,image,nil);precondition(CGImageDestinationFinalize(dst))
}
func bounds(_ image:CGImage)->CGRect {
 let ctx=context(image.width,image.height);ctx.draw(image,in:CGRect(x:0,y:0,width:image.width,height:image.height))
 let data=ctx.data!.assumingMemoryBound(to:UInt8.self)
 var minX=image.width,minY=image.height,maxX=0,maxY=0
 for y in 0..<image.height {for x in 0..<image.width {
  if data[y*ctx.bytesPerRow+x*4+3]>20 {minX=min(minX,x);minY=min(minY,y);maxX=max(maxX,x);maxY=max(maxY,y)}
 }}
 // The decoded bitmap row order matches CGImage crop coordinates.
 return CGRect(x:minX,y:minY,width:maxX-minX+1,height:maxY-minY+1)
}
func build(_ name:String,_ w:Int,_ h:Int,_ delay:Double,_ gifName:String){
 let image=read(inputs.appendingPathComponent("\(name)-sheet.png"))
 let tw=image.width/2,th=image.height/2
 var tiles=[CGImage]();var common=CGRect.null
 for i in 0..<4 {
  let tile=image.cropping(to:CGRect(x:(i%2)*tw,y:(i/2)*th,width:tw,height:th))!
  tiles.append(tile);common=common.union(bounds(tile))
 }
 // A common crop and scale for every frame prevents animation zoom/jitter.
 let pad=6.0, factor=min((Double(w)-pad*2)/common.width,(Double(h)-pad*2)/common.height)
 let rw=common.width*factor,rh=common.height*factor
 let strip=context(w*4,h)
 let gif=CGImageDestinationCreateWithURL(output.appendingPathComponent(gifName) as CFURL,UTType.gif.identifier as CFString,4,nil)!
 CGImageDestinationSetProperties(gif,[kCGImagePropertyGIFDictionary:[kCGImagePropertyGIFLoopCount:0]] as CFDictionary)
 // Keep the first developer frame pixel-identical outside the two hand regions.
 let reference=context(w,h)
 reference.interpolationQuality = .none
 reference.draw(tiles[0].cropping(to:common)!,in:CGRect(x:(Double(w)-rw)/2,y:pad,width:rw,height:rh))
 let base=reference.makeImage()!
 if name == "developer" {
  // Reuse the existing closed-eye source frame; do not change the body or hands.
  let closed=context(w,h),blink=context(w,h)
  closed.interpolationQuality = .none
  closed.draw(tiles[3].cropping(to:common)!,in:CGRect(x:(Double(w)-rw)/2,y:pad,width:rw,height:rh))
  blink.draw(base,in:CGRect(x:0,y:0,width:w,height:h))
  let target=blink.data!.assumingMemoryBound(to:UInt8.self),source=closed.data!.assumingMemoryBound(to:UInt8.self)
  for (eye,rect) in [(300,348,36,66),(404,348,36,66)].enumerated() {
   // Remove the open eye with the original adjacent skin, retaining its row gradient.
   for y in 352..<409 {for x in (rect.0+2)..<(rect.0+rect.2-2) {
    let pixel=y*blink.bytesPerRow+x*4
    for channel in 0..<4 {target[pixel+channel]=target[y*blink.bytesPerRow+375*4+channel]}
   }}
   // Reposition only the real closed-eyelid shape from source frame 4.
   let sx=eye == 0 ? 275 : 376,sw=eye == 0 ? 39 : 40,dx=eye == 0 ? 300 : 406
   for y in 0..<10 {for x in 0..<32 {
    let offset=(382+y*12/10)*closed.bytesPerRow+(sx+x*sw/32)*4
    if source[offset]<50 && source[offset+1]<50 && source[offset+2]<50 && source[offset+3]>220 {
     for channel in 0..<4 {target[(378+y)*blink.bytesPerRow+(dx+x)*4+channel]=source[offset+channel]}
    }
   }}
  }
  save(blink.makeImage()!,"developer_blink.png")
 }
 for i in 0..<4 {
  let ctx=context(w,h)
  if name == "developer" {
   ctx.draw(base,in:CGRect(x:0,y:0,width:w,height:h))
   let row=ctx.bytesPerRow
   let data=ctx.data!.assumingMemoryBound(to:UInt8.self)
   let original=Array(UnsafeBufferPointer(start:data,count:row*h))
   // Alternate subtle 10px finger lifts; head, face, hair and torso never change.
   let hands=[(274,536,110,94),(404,536,106,94)]
   for (hand,rect) in hands.enumerated() {
    let offset=(i == 1 && hand == 0) || (i == 3 && hand == 1) ? -10 : 0
    for y in rect.1..<(rect.1+rect.3) {for x in rect.0..<(rect.0+rect.2) {
     let sourceY=min(h-1,max(rect.1,y-offset))
     for channel in 0..<4 {data[y*row+x*4+channel]=original[sourceY*row+x*4+channel]}
    }}
   }
  } else {
   ctx.interpolationQuality = .none
   let anchor=bounds(tiles[0]),current=bounds(tiles[i])
   let dx=((anchor.minX-current.minX)*factor).rounded(),dy=((current.maxY-anchor.maxY)*factor).rounded()
   ctx.draw(tiles[i].cropping(to:common)!,in:CGRect(x:(Double(w)-rw)/2+dx,y:pad+dy,width:rw,height:rh))
  }
  let frame=ctx.makeImage()!
  strip.draw(frame,in:CGRect(x:i*w,y:0,width:w,height:h))
  if i==0 {save(frame,"\(name)_idle.png")}
  CGImageDestinationAddImage(gif,frame,[kCGImagePropertyGIFDictionary:[kCGImagePropertyGIFDelayTime:delay,kCGImagePropertyGIFUnclampedDelayTime:delay]] as CFDictionary)
 }
 precondition(CGImageDestinationFinalize(gif));save(strip.makeImage()!,"\(name)_strip.png")
 print("\(name): 4 transparent frames \(w)x\(h), loop \(delay*4)s, common crop \(common)")
}
if !CommandLine.arguments.contains("--laptop-only") { build("developer",512,640,0.24,"developer_typing.gif") }
if !CommandLine.arguments.contains("--developer-only") {
if !CommandLine.arguments.contains("--laptop-only") { build("cat",512,288,0.6,"cat_sleeping.gif") }
let catWalkSheet=inputs.appendingPathComponent("cat-walk-sheet.png")
if FileManager.default.fileExists(atPath:catWalkSheet.path) {
 build("cat-walk",512,288,0.12,"cat_walking.gif")
}
let silver=inputs.appendingPathComponent("laptop-silver-clean.png")
let hasSilver=FileManager.default.fileExists(atPath:silver.path)
let raw=read(hasSilver ? silver : inputs.appendingPathComponent("laptop-original.png"))
let clean=context(raw.width,raw.height)
clean.draw(raw,in:CGRect(x:0,y:0,width:raw.width,height:raw.height))
if hasSilver {
 let p=clean.data!.assumingMemoryBound(to:UInt8.self)
 for y in 0..<raw.height {for x in 0..<raw.width {
  let i=y*clean.bytesPerRow+x*4,a=Int(p[i+3])
  if a<224 {p[i]=0;p[i+1]=0;p[i+2]=0;p[i+3]=0}
  else {for c in 0..<3 {p[i+c]=UInt8(min(255,Int(p[i+c])*255/a))};p[i+3]=255}
 }}
}
let laptop=clean.makeImage()!
let crop=laptop.cropping(to:bounds(laptop))!,ctx=context(640,336)
let scale=min(628.0/Double(crop.width),324.0/Double(crop.height))
let w=Double(crop.width)*scale,h=Double(crop.height)*scale
ctx.interpolationQuality = .none
ctx.draw(crop,in:CGRect(x:(640-w)/2,y:6,width:w,height:h))
save(ctx.makeImage()!,hasSilver ? "laptop_silver.png" : "laptop_static.png")
print("laptop: transparent 640x336, source aspect preserved")

}

// Closed lid shares the open laptop canvas and bottom-center anchor.
let closedSource=inputs.appendingPathComponent("laptop-closed-source.png")
if FileManager.default.fileExists(atPath:closedSource.path) {
 let raw=read(closedSource),clean=context(raw.width,raw.height)
 clean.draw(raw,in:CGRect(x:0,y:0,width:raw.width,height:raw.height))
 let p=clean.data!.assumingMemoryBound(to:UInt8.self)
 for y in 0..<raw.height {for x in 0..<raw.width {
  let i=y*clean.bytesPerRow+x*4,a=Int(p[i+3])
  if a<224 {p[i]=0;p[i+1]=0;p[i+2]=0;p[i+3]=0}
  else {for c in 0..<3 {p[i+c]=UInt8(min(255,Int(p[i+c])*255/a))};p[i+3]=255}
 }}
 let image=clean.makeImage()!,crop=image.cropping(to:bounds(image))!,canvas=context(640,336)
 let factor=min(628.0/Double(crop.width),200.0/Double(crop.height))
 let w=Double(crop.width)*factor,h=Double(crop.height)*factor
 canvas.interpolationQuality = .none
 canvas.draw(crop,in:CGRect(x:(640-w)/2,y:6,width:w,height:h))
 save(canvas.makeImage()!,"laptop_closed.png")
 print("closed laptop: transparent 640x336, shared bottom-center anchor")
}
