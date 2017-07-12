import tarfile
import io


# test_string must be a b''
def streamed_archive(test_string):

    outputStream = io.BytesIO()
    tar = tarfile.open(fileobj=outputStream, mode='w:gz')

    inputStream = io.BytesIO(test_string)

    tarinfo = tarfile.TarInfo(name="test_file")
    tarinfo.size = len(inputStream.getbuffer())

    tar.addfile(tarinfo, inputStream)
    tar.close()

    outputStream.seek(0)

    return outputStream

if __name__ == '__main__':
    print(streamed_archive(b'toto'))
