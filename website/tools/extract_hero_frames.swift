// Extract blended frames for make_hero_gif.py; source.mp4 output-directory
// macOS media tooling only; not needed for the website build or deployment.
import Foundation
import AVFoundation
import CoreImage
import ImageIO
import UniformTypeIdentifiers

let input = AVURLAsset(url: URL(fileURLWithPath: CommandLine.arguments[1]))
let output = URL(fileURLWithPath: CommandLine.arguments[2])
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
let fps = 20
let frameCount = 5 * fps
let overlap = fps
let generator = AVAssetImageGenerator(asset: input)
generator.appliesPreferredTrackTransform = true
generator.requestedTimeToleranceBefore = .zero
generator.requestedTimeToleranceAfter = .zero
generator.maximumSize = CGSize(width: 640, height: 360)
let context = CIContext(options: [.useSoftwareRenderer: true])
var frames: [CGImage] = []
for index in 0..<frameCount {
    let time = CMTime(value: Int64(index), timescale: Int32(fps))
    frames.append(try generator.copyCGImage(at: time, actualTime: nil))
}
// Start after the overlap. The final blended frame flows directly into this
// frame on repeat, with no duplicated endpoint, reverse motion, or hold.
for index in overlap..<frameCount {
    var frame = frames[index]
    if index >= frameCount - overlap {
        let headIndex = index - (frameCount - overlap)
        let t = Double(headIndex) / Double(overlap - 1)
        let smooth = t * t * (3 - 2 * t)
        let blend = CIFilter(name: "CIDissolveTransition", parameters: [
            kCIInputImageKey: CIImage(cgImage: frames[index]),
            kCIInputTargetImageKey: CIImage(cgImage: frames[headIndex]),
            kCIInputTimeKey: smooth
        ])!.outputImage!
        frame = context.createCGImage(blend, from: CGRect(x: 0, y: 0, width: frame.width, height: frame.height))!
    }
    let url = output.appendingPathComponent(String(format: "%03d.png", index - overlap))
    let still = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(still, frame, nil)
    guard CGImageDestinationFinalize(still) else { fatalError("Frame export failed") }
}
print("Created \(frameCount - overlap) blended frames at \(fps) fps.")
