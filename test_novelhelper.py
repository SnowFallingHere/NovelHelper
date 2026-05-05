import unittest
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from NovelHelper import FileManager, LanguageManager, ConfigManager, file_manager, language_manager


class TestFileManager(unittest.TestCase):
    def setUp(self):
        self.fm = FileManager('zh_CN')

    def test_num_to_chinese(self):
        self.assertEqual(FileManager.num_to_chinese(1), '一')
        self.assertEqual(FileManager.num_to_chinese(10), '十')
        self.assertEqual(FileManager.num_to_chinese(100), '一百')

    def test_num_to_chinese_upper(self):
        self.assertEqual(FileManager.num_to_chinese_upper(1), '壹')
        self.assertEqual(FileManager.num_to_chinese_upper(10), '拾')

    def test_get_chapter_number(self):
        self.assertEqual(self.fm.get_chapter_number("1第一章_测试.txt"), 1)
        self.assertEqual(self.fm.get_chapter_number("10第十章_测试.txt"), 10)
        self.assertIsNone(self.fm.get_chapter_number("abc.txt"))

    def test_generate_chapter_name_zh(self):
        self.fm.set_language('zh_CN')
        name = self.fm.generate_chapter_name(1, "测试")
        self.assertIn("1", name)
        self.assertIn("一章", name)

    def test_generate_chapter_name_en(self):
        self.fm.set_language('en_US')
        name = self.fm.generate_chapter_name(1, "test")
        self.assertIn("Chapter", name)

    def test_is_numeric_volume_folder(self):
        self.assertTrue(FileManager.is_numeric_volume_folder("1[test]"))
        self.assertTrue(FileManager.is_numeric_volume_folder("10"))
        self.assertFalse(FileManager.is_numeric_volume_folder("abc"))

    def test_get_volume_number(self):
        self.assertEqual(FileManager.get_volume_number("1[test]"), 1)
        self.assertEqual(FileManager.get_volume_number("10[old_500]"), 10)
        self.assertIsNone(FileManager.get_volume_number("abc"))

    def test_is_old_volume(self):
        self.assertTrue(FileManager.is_old_volume("1[old_500]"))
        self.assertFalse(FileManager.is_old_volume("1[new_500]"))
        self.assertFalse(FileManager.is_old_volume("1[test]"))

    def test_format_volume_title_export(self):
        result = self.fm.format_volume_title_export(1, "测试卷", 1000)
        self.assertIn("1", result)
        self.assertIn("测试卷", result)

    def test_format_chapter_title_export(self):
        result = self.fm.format_chapter_title_export(1, "测试章")
        self.assertIn("1", result)
        self.assertIn("测试章", result)

    def test_set_language(self):
        self.fm.set_language('en_US')
        self.assertEqual(self.fm._current_lang, 'en_US')
        self.fm.set_language('zh_CN')
        self.assertEqual(self.fm._current_lang, 'zh_CN')

    def test_is_default_content(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("第1个文件")
            temp_path = f.name
        try:
            self.assertTrue(FileManager.is_default_content(temp_path))
        finally:
            os.unlink(temp_path)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("这是正常内容")
            temp_path = f.name
        try:
            self.assertFalse(FileManager.is_default_content(temp_path))
        finally:
            os.unlink(temp_path)

    def test_get_word_count(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("测试内容")
            temp_path = f.name
        try:
            count, err = self.fm.get_word_count(temp_path)
            self.assertIsNone(err)
            self.assertGreater(count, 0)
        finally:
            os.unlink(temp_path)

        count, err = self.fm.get_word_count("/nonexistent/path.txt")
        self.assertEqual(count, 0)


class TestLanguageManager(unittest.TestCase):
    def setUp(self):
        self.lm = LanguageManager()

    def test_default_translations_exist(self):
        self.assertIn('zh_CN', LanguageManager.DEFAULT_TRANSLATIONS)
        self.assertIn('en_US', LanguageManager.DEFAULT_TRANSLATIONS)
        self.assertIn('ja_JP', LanguageManager.DEFAULT_TRANSLATIONS)

    def test_get_current_language(self):
        lang = self.lm.get_current_language()
        self.assertIn(lang, ['zh_CN', 'en_US', 'ja_JP'])

    def test_set_current_language(self):
        original = self.lm.get_current_language()
        self.lm.set_current_language('en_US')
        self.assertEqual(self.lm.get_current_language(), 'en_US')
        self.lm.set_current_language(original)

    def test_tr_returns_value(self):
        result = self.lm.tr('app_title')
        self.assertIsNotNone(result)
        self.assertNotEqual(result, 'app_title')

    def test_tr_returns_key_for_missing(self):
        result = self.lm.tr('nonexistent_key_12345')
        self.assertEqual(result, 'nonexistent_key_12345')

    def test_validate_translations(self):
        missing = self.lm.validate_translations()
        self.assertIsInstance(missing, dict)

    def test_get_available_languages(self):
        langs = self.lm.get_available_languages()
        self.assertIn('zh_CN', langs)
        self.assertIn('en_US', langs)


class TestConfigManager(unittest.TestCase):
    def test_get_with_fallback(self):
        value = ConfigManager.get('NonExistentSection', 'NonExistentKey', fallback='default')
        self.assertEqual(value, 'default')

    def test_set_and_get(self):
        ConfigManager.set('TestSection', 'TestKey', 'TestValue')
        value = ConfigManager.get('TestSection', 'TestKey', fallback='wrong')
        self.assertEqual(value, 'TestValue')
        ConfigManager.remove_option('TestSection', 'TestKey')

    def test_get_int_with_fallback(self):
        value = ConfigManager.get_int('NonExistentSection', 'NonExistentKey', fallback=42)
        self.assertEqual(value, 42)


class TestFileManagerEdgeCases(unittest.TestCase):
    def setUp(self):
        self.fm = FileManager('zh_CN')

    def test_format_chapter_no_name(self):
        name = self.fm.generate_chapter_name(5, "")
        self.assertIn("5", name)

    def test_format_chapter_with_title(self):
        name = self.fm.generate_chapter_name(5, "测试")

    def test_extract_volume_name(self):
        result = self.fm.extract_volume_name("1[测试卷]")
        self.assertEqual(result, "测试卷")
        result = self.fm.extract_volume_name("1")
        self.assertIsNone(result)

    def test_replace_dash_with_space(self):
        result = self.fm.replace_dash_with_space("hello-world")
        self.assertEqual(result, "hello world")


if __name__ == '__main__':
    unittest.main()
