"""测试数据摄取模块"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import RAW_DATA_DIR


class TestFileScanner:
    def test_scan_finds_files(self):
        from src.ingestion import FileScanner
        scanner = FileScanner()
        files = scanner.scan(str(RAW_DATA_DIR))
        assert len(files) > 0, "应该找到至少一个文件"
        for f in files:
            assert 'path' in f
            assert 'name' in f
            assert 'extension' in f
            assert 'size' in f

    def test_supported_extensions(self):
        from src.ingestion import FileScanner
        from config.settings import SUPPORTED_EXTENSIONS
        scanner = FileScanner()
        files = scanner.scan(str(RAW_DATA_DIR))
        for f in files:
            assert f['extension'] in SUPPORTED_EXTENSIONS, \
                f"不支持的文件格式: {f['extension']}"


class TestTXTReader:
    def test_read_txt(self):
        from src.ingestion import FileScanner, TXTReader
        scanner = FileScanner()
        files = scanner.scan(str(RAW_DATA_DIR))
        txt_files = [f for f in files if f['extension'] == '.txt']

        if not txt_files:
            return

        reader = TXTReader()
        content = reader.read(txt_files[0]['path'])
        assert content is not None
        assert len(content) > 0


class TestHTMLReader:
    def test_read_html(self):
        from src.ingestion import FileScanner, HTMLReader
        scanner = FileScanner()
        files = scanner.scan(str(RAW_DATA_DIR))
        html_files = [f for f in files if f['extension'] in ['.html', '.htm']]

        if not html_files:
            return

        reader = HTMLReader()
        title, text = reader.read_with_title(html_files[0]['path'])
        assert text is not None
        assert len(text) > 0


class TestMetadataExtractor:
    def test_extract_from_csv(self):
        from src.ingestion import FileScanner, MetadataExtractor
        csv_path = project_root / "data" / "raw" / "metadata.csv"

        scanner = FileScanner()
        files = scanner.scan(str(RAW_DATA_DIR))
        if not files:
            return

        extractor = MetadataExtractor(str(csv_path) if csv_path.exists() else None)
        metadata = extractor.extract(files[0]['path'])

        assert 'file_name' in metadata
        assert 'title' in metadata
        assert 'author' in metadata
        assert 'date' in metadata
        assert 'category' in metadata

    def test_extract_without_csv(self):
        from src.ingestion import FileScanner, MetadataExtractor
        scanner = FileScanner()
        files = scanner.scan(str(RAW_DATA_DIR))
        if not files:
            return

        extractor = MetadataExtractor()
        metadata = extractor.extract(files[0]['path'])
        assert 'file_name' in metadata
        assert 'title' in metadata
