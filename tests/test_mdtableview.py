import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mdtableview as mv


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def get(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class BakeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        put(os.path.join(self.d, "a.md"),
            "---\ntags: [x]\n---\n# Page A\n\n[b](sub/b.md#top) · [web](https://example.com) · [pic](img/p.png) · [here](#x)\n\n"
            "![p](img/p.png)\n\n| k | v |\n|---|---|\n| 1 | 2 |\n")
        put(os.path.join(self.d, "sub", "b.md"), "no heading\n\n[a](../a.md)\n")
        put(os.path.join(self.d, "_html", "stale.md"), "# must not be baked\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_folder(self):
        written, start = mv.bake([self.d])
        out = os.path.join(self.d, "_html")
        self.assertEqual(start, os.path.join(out, "index.html"))
        self.assertEqual(len(written), 3)                       # a, sub/b, index — _html/stale.md is skipped
        a = get(os.path.join(out, "a.html"))
        self.assertIn("<title>Page A</title>", a)
        self.assertNotIn("tags:", a)                            # front matter stripped
        self.assertIn('href="sub/b.html#top"', a)               # baked .md → .html, fragment kept
        self.assertIn('href="https://example.com"', a)
        self.assertIn('href="#x"', a)
        self.assertIn('href="../img/p.png"', a)                 # other relative links re-based on the source
        self.assertIn('src="../img/p.png"', a)
        self.assertIn('<div class="tw"><table>', a)
        b = get(os.path.join(out, "sub", "b.html"))
        self.assertIn("<title>b</title>", b)                    # no heading → file name
        self.assertIn('href="../a.html"', b)
        self.assertIn('href="../index.html"', b)

    def test_single_file_and_determinism(self):
        out = os.path.join(self.d, "site")
        written, start = mv.bake([os.path.join(self.d, "a.md")], out, theme="light")
        self.assertEqual(written, [os.path.join(out, "a.html")])
        self.assertEqual(start, written[0])
        first = get(start)
        self.assertNotIn("prefers-color-scheme", first)
        self.assertIn('href="../sub/b.md#top"', first)          # b.md was not baked → link points at the source
        mv.bake([os.path.join(self.d, "a.md")], out, theme="light")
        self.assertEqual(first, get(start))


if __name__ == "__main__":
    unittest.main()
