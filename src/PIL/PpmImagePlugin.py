#
# The Python Imaging Library.
# $Id$
#
# PPM support for PIL
#
# History:
#       96-03-24 fl     Created
#       98-03-06 fl     Write RGBA images (as RGB, that is)
#
# Copyright (c) Secret Labs AB 1997-98.
# Copyright (c) Fredrik Lundh 1996.
#
# See the README file for information on usage and redistribution.
#


from . import Image, ImageFile

#
# --------------------------------------------------------------------

B_WHITESPACE = b"\x20\x09\x0a\x0b\x0c\x0d"

MODES = {
    # standard, plain
    b"P1": ("plain", "1"),
    b"P2": ("plain", "L"),
    b"P3": ("plain", "RGB"),
    # standard, raw
    b"P4": ("raw", "1"),
    b"P5": ("raw", "L"),
    b"P6": ("raw", "RGB"),
    # extensions
    b"P0CMYK": ("raw", "CMYK"),
    # PIL extensions (for test purposes only)
    b"PyP": ("raw", "P"),
    b"PyRGBA": ("raw", "RGBA"),
    b"PyCMYK": ("raw", "CMYK"),
}


def _accept(prefix):
    return prefix[0:1] == b"P" and prefix[1] in b"0123456y"


##
# Image plugin for PBM, PGM, and PPM images.


class PpmImageFile(ImageFile.ImageFile):

    format = "PPM"
    format_description = "Pbmplus image"

    def _read_magic(self, magic=b""):
        while True:  # read until next whitespace
            c = self.fp.read(1)
            if c in B_WHITESPACE:
                break
            magic += c
            if len(magic) > 6:  # exceeded max magic number length
                break
        return magic

    def _read_token(self, token=b""):
        def _ignore_comment():  # ignores rest of the line; stops at CR, LF or EOF
            while self.fp.read(1) not in b"\r\n":
                pass

        while True:  # read until non-whitespace is found
            c = self.fp.read(1)
            if c == b"#":  # found comment, ignore it
                _ignore_comment()
                continue
            if c in B_WHITESPACE:  # found whitespace, ignore it
                if c == b"":  # reached EOF
                    raise ValueError("Reached EOF while reading header")
                continue
            break

        token += c

        while True:  # read until next whitespace
            c = self.fp.read(1)
            if c == b"#":
                _ignore_comment()
                continue
            if c in B_WHITESPACE:  # token ended
                break
            token += c
            if len(token) > 10:
                raise ValueError(f"Token too long in file header: {token}")
        return token

    def _open(self):
        magic_number = self._read_magic()
        try:
            decoder, mode = MODES[magic_number]
        except KeyError:
            raise SyntaxError("Not a PPM image file") from None

        self.custom_mimetype = {
            b"P1": "image/x-portable-bitmap",
            b"P2": "image/x-portable-graymap",
            b"P3": "image/x-portable-pixmap",
            b"P4": "image/x-portable-bitmap",
            b"P5": "image/x-portable-graymap",
            b"P6": "image/x-portable-pixmap",
        }.get(magic_number)

        for ix in range(3):
            token = self._read_token()
            try:  # check token sanity
                token = int(token)
            except ValueError:
                raise ValueError(
                    f"Non-decimal-ASCII found in header: {token}"
                ) from None
            if ix == 0:  # token is the x size
                xsize = token
            elif ix == 1:  # token is the y size
                ysize = token
                if mode == "1":
                    self.mode = "1"
                    rawmode = "1;I"
                    break
                else:
                    self.mode = rawmode = mode
            elif ix == 2:  # token is maxval
                maxval = token
                if maxval > 255:
                    if not mode == "L":
                        raise ValueError(f"Too many colors for band: {maxval}")
                    if maxval < 2 ** 16:
                        self.mode = "I"
                        rawmode = "I;16B"
                    else:
                        self.mode = "I"
                        rawmode = "I;32B"

        self._size = xsize, ysize
        self.tile = [
            (
                decoder,  # decoder
                (0, 0, xsize, ysize),  # region: whole image
                self.fp.tell(),  # offset to image data
                (rawmode, 0, 1),  # parameters for decoder
            )
        ]


#
# --------------------------------------------------------------------


def _save(im, fp, filename):
    if im.mode == "1":
        rawmode, head = "1;I", b"P4"
    elif im.mode == "L":
        rawmode, head = "L", b"P5"
    elif im.mode == "I":
        if im.getextrema()[1] < 2 ** 16:
            rawmode, head = "I;16B", b"P5"
        else:
            rawmode, head = "I;32B", b"P5"
    elif im.mode == "RGB":
        rawmode, head = "RGB", b"P6"
    elif im.mode == "RGBA":
        rawmode, head = "RGB", b"P6"
    else:
        raise OSError(f"Cannot write mode {im.mode} as PPM")
    fp.write(head + ("\n%d %d\n" % im.size).encode("ascii"))
    if head == b"P6":
        fp.write(b"255\n")
    if head == b"P5":
        if rawmode == "L":
            fp.write(b"255\n")
        elif rawmode == "I;16B":
            fp.write(b"65535\n")
        elif rawmode == "I;32B":
            fp.write(b"2147483648\n")
    ImageFile._save(im, fp, [("raw", (0, 0) + im.size, 0, (rawmode, 0, 1))])

    # ALTERNATIVE: save via builtin debug function
    # im._dump(filename)


#
# --------------------------------------------------------------------


Image.register_open(PpmImageFile.format, PpmImageFile, _accept)
Image.register_save(PpmImageFile.format, _save)

Image.register_extensions(PpmImageFile.format, [".pbm", ".pgm", ".ppm", ".pnm"])

Image.register_mime(PpmImageFile.format, "image/x-portable-anymap")
