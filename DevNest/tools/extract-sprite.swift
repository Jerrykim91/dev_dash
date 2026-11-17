import Foundation
import ImageIO
import CoreGraphics
import UniformTypeIdentifiers
let src=CGImageSourceCreateWithURL(URL(fileURLWithPath:CommandLine.arguments[1]) as CFURL,nil)!
let first=CGImageSourceCreateImageAtIndex(src,0,nil)!
let count=CGImageSourceGetCount(src), w=first.width, h=first.height
let ctx=CGContext(data:nil,width:w*count,height:h,bitsPerComponent:8,bytesPerRow:0,space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue)!
for i in 0..<count {
 let frame=CGImageSourceCreateImageAtIndex(src,i,nil)!
 ctx.draw(frame,in:CGRect(x:i*w,y:0,width:w,height:h))
}
let dst=CGImageDestinationCreateWithURL(URL(fileURLWithPath:CommandLine.arguments[2]) as CFURL,UTType.png.identifier as CFString,1,nil)!
CGImageDestinationAddImage(dst,ctx.makeImage()!,nil)
guard CGImageDestinationFinalize(dst) else {fatalError("write failed")}
print("Extracted \(count) original GIF frames: \(w*count)x\(h), no redrawing")
