from PIL import Image, ImageDraw

sizes = [16, 24, 32, 48, 64, 128, 256]
images=[]
for size in sizes:
    im=Image.new("RGBA", (size,size), (16,18,20,255))
    d=ImageDraw.Draw(im)
    pad=max(1,size//10)
    d.ellipse((pad,pad,size-pad,size-pad), fill=(244,123,32,255))
    # Simple white leaf + A mark, crisp at small sizes.
    d.polygon([(size*0.28,size*0.63),(size*0.44,size*0.30),(size*0.62,size*0.24),(size*0.72,size*0.30),(size*0.66,size*0.48),(size*0.50,size*0.62)], fill=(255,255,255,255))
    d.rectangle((size*0.43,size*0.60,size*0.57,size*0.68), fill=(16,18,20,255))
    d.polygon([(size*0.40,size*0.68),(size*0.50,size*0.43),(size*0.60,size*0.68)], fill=(255,255,255,255))
    d.rectangle((size*0.46,size*0.58,size*0.54,size*0.61), fill=(244,123,32,255))
    images.append(im)
images[0].save("agrostar.ico", format="ICO", sizes=[(s,s) for s in sizes], append_images=images[1:])
print("Icon created")
