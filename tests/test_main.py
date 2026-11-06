import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import main
from shop.config import DATABASE_PATH


class MainTests(unittest.TestCase):
    def test_database_path_is_project_constant(self):
        self.assertEqual(DATABASE_PATH, Path(main.__file__).resolve().with_name("shop.sqlite3"))

    def test_database_argument_is_not_accepted(self):
        with patch.object(sys, "argv", ["main.py", "--database", "other.db"]):
            with patch("sys.stderr"):
                with self.assertRaises(SystemExit) as error:
                    main.main()
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
