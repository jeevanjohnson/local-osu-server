def _read_uleb128(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0

    while True:
        if offset >= len(data):
            raise ValueError("Unexpected end of data while reading ULEB128")

        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift

        if (byte & 0x80) == 0:
            break

        shift += 7

    return value, offset

def _read_osr_string(data: bytes, offset: int) -> tuple[str, int]:
    if offset >= len(data):
        raise ValueError("Unexpected end of data while reading string marker")

    marker = data[offset]
    offset += 1

    if marker == 0x00:
        return "", offset

    if marker != 0x0B:
        raise ValueError(f"Invalid .osr string marker: {marker}")

    length, offset = _read_uleb128(data, offset)
    end = offset + length
    if end > len(data):
        raise ValueError("Unexpected end of data while reading string body")

    return data[offset:end].decode(errors="ignore"), end

def extract_replay_frames_from_osr(osr_data: bytes) -> tuple[bytes, str]:
    """Extract the LZMA replay-frame section from a full .osr payload."""
    """Returns a tuple of (replay_frames, beatmap_md5)"""
    offset = 0

    # mode (1), version (4)
    offset += 1 + 4

    # beatmap_md5, username, replay_md5
    beatmap_md5, offset = _read_osr_string(osr_data, offset)
    _, offset = _read_osr_string(osr_data, offset)
    _, offset = _read_osr_string(osr_data, offset)

    # 300/100/50/geki/katu/miss (2 * 6), score (4), combo (2), perfect (1), mods (4)
    offset += (2 * 6) + 4 + 2 + 1 + 4

    # life bar string, timestamp (8)
    _, offset = _read_osr_string(osr_data, offset)
    offset += 8

    # replay data length (int32 little endian)
    if offset + 4 > len(osr_data):
        raise ValueError("Unexpected end of data while reading replay length")

    replay_length = int.from_bytes(osr_data[offset:offset + 4], "little", signed=True)
    offset += 4

    if replay_length < 0:
        raise ValueError("Invalid replay frame length in .osr payload")

    end = offset + replay_length
    if end > len(osr_data):
        raise ValueError("Replay frame length exceeds .osr payload size")

    return osr_data[offset:end], beatmap_md5