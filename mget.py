# Usage: python mget.py [options] url
# A multi threaded download manager, written in Python without any external dependencies.
# By ruzhila.cn, a backend developer campus  2024-04-26

import sys
import os
import threading
import time
from optparse import OptionParser
import urllib3
from urllib.parse import urlparse
from queue import Queue

parser = OptionParser()
parser.add_option("-t", dest="thread",
                  default=4, help="number of threads")
parser.add_option("-o", dest="output",
                  default=None,
                  help="output file")
parser.add_option("--timeout", dest="timeout",
                  default=60, help="timeout seconds")

pool = urllib3.PoolManager()


def download(progress: Queue, outout_fd: int, url: str, start_pos: int, end_pos: int):
    headers = {'Range': 'bytes=%d-%d' % (start_pos, end_pos)}
    response = pool.request('GET', url, headers=headers, preload_content=False)
    fd = os.dup(outout_fd)
    pos = start_pos
    for chunk in response.stream(2048):
        os.lseek(fd, pos, os.SEEK_SET)
        os.write(fd, chunk)
        pos += len(chunk)
        progress.put(len(chunk))


if __name__ == '__main__':
    (options, args) = parser.parse_args()
    if len(args) < 1:
        print("Usage: python mget.py [options] url")
        sys.exit(1)

    url = args[0]
    if not url.startswith("http"):
        print("Invalid URL")
        sys.exit(1)

    file_size = int(pool.request(
        'HEAD', url).headers.get('content-length', '0'))

    if file_size == 0:
        print("Invalid file size")
        sys.exit(1)

    file_name = options.output or os.path.basename(urlparse(url).path)
    print("Downloading %s to %s, size: %d, thread: %d" %
          (url, file_name, file_size, int(options.thread)))

    file = open(file_name, 'wb')
    file.seek(file_size - 1)
    file.write(b'\0')
    file.seek(0)

    outout_fd = file.fileno()
    progress = Queue()
    st = time.time()

    for i in range(int(options.thread)):
        start = file_size // int(options.thread) * i
        end = file_size // int(options.thread) * (i + 1) - 1

        if i == int(options.thread) - 1:
            end = file_size

        t = threading.Thread(target=lambda: download(progress,
                                                     outout_fd, url, start, end))
        t.start()

    downloaded = 0
    while True:
        percent = ("{0:.1f}").format(100 * (downloaded / float(file_size)))
        filled_length = int(round(50 * downloaded / float(file_size)))
        bar = '█' * filled_length + '-' * (50 - filled_length)
        sys.stdout.write('\r%s |%s| %s%% %s' %
                         ('Progress:', bar, percent, 'Complete')),
        sys.stdout.flush()
        if downloaded == file_size:
            break
        p = progress.get(True, int(options.timeout))
        if p == -1:
            print("\nDownload failed")
            sys.exit(1)
        downloaded += p

    print("\nDownload completed in %f seconds" % (time.time() - st))
