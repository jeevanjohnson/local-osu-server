"""Tests for osu_watcher.parser module."""

import pytest
import tempfile
from pathlib import Path
from osu_watcher.parser import parse_osu_file


class TestParseOsuFile:
    """Test suite for parse_osu_file function."""

    def test_happy_path_valid_osu_file(self, tmp_path):
        """Parse a valid .osu file with all metadata."""
        # Create a temporary .osu file
        beatmap_folder = tmp_path / "123 Artist - Song"
        beatmap_folder.mkdir()
        
        osu_file = beatmap_folder / "song.osu"
        content = b"""[General]
Name:Song
Artist:Artist

[Metadata]
Title:Song
TitleUnicode:Song
Artist:Artist
ArtistUnicode:Artist
Creator:Mapper
Version:Easy
Source:
Tags:
BeatmapID:456
BeatmapSetID:123
"""
        osu_file.write_bytes(content)
        
        result = parse_osu_file(osu_file)
        
        assert result["filename"] == "song.osu"
        assert result["beatmap_id"] == 456
        assert result["beatmap_set_id"] == 123
        assert isinstance(result["md5"], str)
        assert len(result["md5"]) == 32  # MD5 hex is 32 chars
        assert result["path"] == osu_file.resolve()

    def test_happy_path_minimal_osu_file(self, tmp_path):
        """Parse a minimal .osu file with only required fields."""
        beatmap_folder = tmp_path / "789 Artist"
        beatmap_folder.mkdir()
        
        osu_file = beatmap_folder / "minimal.osu"
        content = b"""[General]
Name:Test

[Metadata]
BeatmapID:999
"""
        osu_file.write_bytes(content)
        
        result = parse_osu_file(osu_file)
        
        assert result["filename"] == "minimal.osu"
        assert result["beatmap_id"] == 999
        assert result["beatmap_set_id"] == 789
        assert isinstance(result["md5"], str)

    def test_edge_case_no_beatmap_id(self, tmp_path):
        """Parse .osu file without BeatmapID field."""
        beatmap_folder = tmp_path / "555 Artist"
        beatmap_folder.mkdir()
        
        osu_file = beatmap_folder / "no_id.osu"
        content = b"""[General]
Name:Song

[Metadata]
Title:Song
"""
        osu_file.write_bytes(content)
        
        result = parse_osu_file(osu_file)
        
        assert result["beatmap_id"] is None
        assert result["beatmap_set_id"] == 555

    def test_edge_case_no_set_id_in_folder_name(self, tmp_path):
        """Parse file in folder without set ID prefix."""
        beatmap_folder = tmp_path / "No Number Here"
        beatmap_folder.mkdir()
        
        osu_file = beatmap_folder / "song.osu"
        content = b"""[Metadata]
BeatmapID:111
"""
        osu_file.write_bytes(content)
        
        result = parse_osu_file(osu_file)
        
        assert result["beatmap_set_id"] is None
        assert result["beatmap_id"] == 111

    def test_edge_case_beatmap_id_with_spaces(self, tmp_path):
        """Parse .osu file where BeatmapID line has extra spaces."""
        beatmap_folder = tmp_path / "100 Test"
        beatmap_folder.mkdir()
        
        osu_file = beatmap_folder / "spaces.osu"
        content = b"""[Metadata]
BeatmapID   :   222
"""
        osu_file.write_bytes(content)
        
        result = parse_osu_file(osu_file)
        
        assert result["beatmap_id"] == 222

    def test_edge_case_empty_file(self, tmp_path):
        """Parse empty .osu file."""
        beatmap_folder = tmp_path / "400 Empty"
        beatmap_folder.mkdir()
        
        osu_file = beatmap_folder / "empty.osu"
        osu_file.write_bytes(b"")
        
        result = parse_osu_file(osu_file)
        
        assert result["filename"] == "empty.osu"
        assert result["beatmap_id"] is None
        assert result["beatmap_set_id"] == 400
        assert isinstance(result["md5"], str)

    def test_edge_case_large_beatmap_id(self, tmp_path):
        """Parse file with very large beatmap ID."""
        beatmap_folder = tmp_path / "999999 BigSet"
        beatmap_folder.mkdir()
        
        osu_file = beatmap_folder / "big.osu"
        content = b"""[Metadata]
BeatmapID:9999999
"""
        osu_file.write_bytes(content)
        
        result = parse_osu_file(osu_file)
        
        assert result["beatmap_set_id"] == 999999
        assert result["beatmap_id"] == 9999999

    def test_edge_case_beatmap_id_not_in_first_50_lines(self, tmp_path):
        """Parse file where BeatmapID appears after line 50."""
        beatmap_folder = tmp_path / "50 Test"
        beatmap_folder.mkdir()
        
        osu_file = beatmap_folder / "far.osu"
        # Create 60 lines, with BeatmapID on line 55
        lines = [b"Line %d\n" % i for i in range(54)]
        lines.append(b"BeatmapID:333")
        content = b"".join(lines)
        
        osu_file.write_bytes(content)
        
        result = parse_osu_file(osu_file)
        
        # BeatmapID should NOT be found (only first 50 lines checked)
        assert result["beatmap_id"] is None

    def test_edge_case_utf8_sig_encoding(self, tmp_path):
        """Parse file with UTF-8 BOM encoding."""
        beatmap_folder = tmp_path / "200 Unicode"
        beatmap_folder.mkdir()
        
        osu_file = beatmap_folder / "utf8.osu"
        # Write with UTF-8 BOM
        content = "\ufeff[Metadata]\nBeatmapID:444\n".encode("utf-8-sig")
        osu_file.write_bytes(content)
        
        result = parse_osu_file(osu_file)
        
        assert result["beatmap_id"] == 444

    def test_error_case_file_not_found(self, tmp_path):
        """Parsing non-existent file raises error."""
        non_existent = tmp_path / "nonexistent.osu"
        
        with pytest.raises(FileNotFoundError):
            parse_osu_file(non_existent)

    def test_error_case_invalid_encoding(self, tmp_path):
        """Parsing file with invalid UTF-8 encoding raises error."""
        beatmap_folder = tmp_path / "100 Bad"
        beatmap_folder.mkdir()
        
        osu_file = beatmap_folder / "bad_encoding.osu"
        # Write invalid UTF-8 bytes
        osu_file.write_bytes(b"\xff\xfe[Invalid]")
        
        with pytest.raises(UnicodeDecodeError):
            parse_osu_file(osu_file)

    def test_error_case_invalid_beatmap_id_format(self, tmp_path):
        """Parsing file with non-numeric BeatmapID raises error."""
        beatmap_folder = tmp_path / "100 Bad"
        beatmap_folder.mkdir()
        
        osu_file = beatmap_folder / "bad_id.osu"
        content = b"""[Metadata]
BeatmapID:NotANumber
"""
        osu_file.write_bytes(content)
        
        with pytest.raises(ValueError):
            parse_osu_file(osu_file)

    def test_md5_consistency(self, tmp_path):
        """Same file content produces same MD5 hash."""
        beatmap_folder = tmp_path / "100 Test"
        beatmap_folder.mkdir()
        
        osu_file = beatmap_folder / "consistent.osu"
        content = b"[Metadata]\nBeatmapID:555"
        osu_file.write_bytes(content)
        
        result1 = parse_osu_file(osu_file)
        result2 = parse_osu_file(osu_file)
        
        assert result1["md5"] == result2["md5"]

    def test_md5_differs_for_different_content(self, tmp_path):
        """Different file content produces different MD5 hash."""
        beatmap_folder = tmp_path / "100 Test"
        beatmap_folder.mkdir()
        
        osu_file1 = beatmap_folder / "file1.osu"
        osu_file1.write_bytes(b"Content1")
        
        osu_file2 = beatmap_folder / "file2.osu"
        osu_file2.write_bytes(b"Content2")
        
        result1 = parse_osu_file(osu_file1)
        result2 = parse_osu_file(osu_file2)
        
        assert result1["md5"] != result2["md5"]

    def test_path_is_absolute(self, tmp_path):
        """Returned path is always absolute."""
        beatmap_folder = tmp_path / "100 Test"
        beatmap_folder.mkdir()
        
        osu_file = beatmap_folder / "test.osu"
        osu_file.write_bytes(b"[Metadata]\nBeatmapID:100")
        
        result = parse_osu_file(osu_file)
        
        assert result["path"].is_absolute()
        assert result["path"] == osu_file.resolve()
