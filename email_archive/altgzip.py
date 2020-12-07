import gzip

"""
Handle processing zlib-compressed files that may have trailing, non-Gzipped data.
Adapted from https://blog.packetfrenzy.com/ignoring-gzip-trailing-garbage-data-in-python/
"""

class AltGzipFile(gzip.GzipFile):

    def read(self, size=-1):
        chunks = []
        try:
            if size < 0:
                while True:
                    chunk = self.read1()
                    if not chunk:
                        break
                    chunks.append(chunk)
            else:
                while size > 0:
                    chunk = self.read1(size)
                    if not chunk:
                        break
                    size -= len(chunk)
                    chunks.append(chunk)
        except OSError as e:
            if not chunks or not str(e).startswith('Not a gzipped file'):
                raise

        return b''.join(chunks)
