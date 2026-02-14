'use client'

interface Props {
  images: string[]
  name: string
}

export default function ProfilePortfolio({ images, name }: Props) {
  if (images.length === 0) return null

  // Show up to 5 images in a grid: first image spans 2 rows
  const displayImages = images.slice(0, 5)

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      {displayImages.map((src, i) => (
        <div
          key={src}
          className={`relative overflow-hidden rounded-xl cursor-pointer transition-transform hover:scale-[1.02] ${
            i === 0 ? 'row-span-2 sm:row-span-2' : ''
          }`}
          style={{ aspectRatio: i === 0 ? undefined : '4/5' }}
        >
          <img
            src={src}
            alt={`${name} product ${i + 1}`}
            className="w-full h-full object-cover"
            loading="lazy"
          />
          {/* Gradient overlay at bottom */}
          <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-black/30 to-transparent" />
        </div>
      ))}
    </div>
  )
}
