import Foundation
import ImageIO
import CoreGraphics
import UniformTypeIdentifiers

let root = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : FileManager.default.currentDirectoryPath)
let source = root.appendingPathComponent("source-assets/separated-inputs/plants-overlay-source.png")
let output = root.appendingPathComponent("frontend/assets/characters")

func read(_ path: URL) -> CGImage {
  CGImageSourceCreateImageAtIndex(CGImageSourceCreateWithURL(path as CFURL, nil)!, 0, nil)!
}

func save(_ image: CGImage, _ name: String) {
  let destination = CGImageDestinationCreateWithURL(output.appendingPathComponent(name) as CFURL, UTType.png.identifier as CFString, 1, nil)!
  CGImageDestinationAddImage(destination, image, nil)
  precondition(CGImageDestinationFinalize(destination))
}

func alphaBounds(_ image: CGImage) -> CGRect {
  let context = CGContext(data: nil, width: image.width, height: image.height, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
  context.draw(image, in: CGRect(x: 0, y: 0, width: image.width, height: image.height))
  let bytes = context.data!.assumingMemoryBound(to: UInt8.self)
  var minX = image.width, minY = image.height, maxX = -1, maxY = -1
  for y in 0..<image.height {
    for x in 0..<image.width where bytes[y * context.bytesPerRow + x * 4 + 3] > 20 {
      minX = min(minX, x); minY = min(minY, y); maxX = max(maxX, x); maxY = max(maxY, y)
    }
  }
  precondition(maxX >= minX && maxY >= minY)
  return CGRect(x: minX, y: minY, width: maxX - minX + 1, height: maxY - minY + 1)
}

let image = read(source)
let regions: [(String, CGRect)] = [
  ("plant_upper_left", CGRect(x: 0, y: 30, width: 250, height: 465)),
  ("plant_desk_left", CGRect(x: 300, y: 355, width: 235, height: 250)),
  ("plant_floor_left", CGRect(x: 0, y: 600, width: 275, height: 270)),
  ("plant_desk_right", CGRect(x: 1060, y: 370, width: 260, height: 255)),
  ("plant_hanging_right", CGRect(x: 1460, y: 0, width: 212, height: 485)),
  ("plant_side_right", CGRect(x: 1470, y: 520, width: 202, height: 275))
]

for (name, region) in regions {
  let tile = image.cropping(to: region)!
  let bounds = alphaBounds(tile).insetBy(dx: -4, dy: -4).intersection(CGRect(x: 0, y: 0, width: tile.width, height: tile.height))
  let crop = tile.cropping(to: bounds)!
  save(crop, "\(name).png")
  let sceneX = region.minX + bounds.midX
  let sceneBottom = region.minY + bounds.maxY
  print("\(name): \(crop.width)x\(crop.height), x=\(sceneX / Double(image.width) * 100), y=\(sceneBottom / Double(image.height) * 100), baseWidth=\(Double(crop.width) / Double(image.width) * 100)")
}
