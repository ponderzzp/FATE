import zlib
import bz2
import lzma
import lzo
import lz4.frame

class BytesCompress:
    def __init__(self, compression_algorithm="Deflate"):
        self.algorithm = compression_algorithm
        self.compressfunc = {
            "Deflate": zlib,
            "Bzip2": bz2,
            "LZMA": lzma,
            "LZO": lzo,
            "LZ4": lz4.frame,
        }
        self.decompressfunc = {
            "Deflate": zlib,
            "Bzip2": bz2,
            "LZMA": lzma,
            "LZO": lzo,
            "LZ4": lz4.frame,
        }
        self.data_compressed = None
        self.data_decompressed = None

    def compress(self, data):
        self.data_compressed = self.compressfunc.get(self.algorithm).compress(data)
        return self.data_compressed

    def uncompress(self, data):
        self.data_decompressed = self.decompressfunc.get(self.algorithm).decompress(data)
        return self.data_decompressed