import tarfile
import io


# test_string must be a b''
def streamed_archive(filename, test_string):

    outputStream = io.BytesIO()
    with tarfile.open(fileobj=outputStream, mode='w:gz') as tar:
        inputStream = io.BytesIO(test_string)
        tarinfo = tarfile.TarInfo(name=filename)
        tarinfo.size = len(inputStream.getbuffer())
        tar.addfile(tarinfo, inputStream)

    outputStream.seek(0)

    return outputStream
