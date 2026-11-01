"""Imágenes aportadas por el propio feed sin confundir multimedia ajena."""
import unittest
from xml.etree import ElementTree as ET

import fetch_noticias as news


class RssImageTests(unittest.TestCase):
    def test_nested_media_group_image(self):
        node = ET.fromstring('''<item xmlns:media="http://search.yahoo.com/mrss/">
            <title>Una noticia</title><media:group>
              <media:content type="video/mp4" url="https://editor.example/video.mp4"/>
              <media:thumbnail url="https://editor.example/foto.jpg"/>
            </media:group></item>''')
        self.assertEqual(news.rss_image(node), "https://editor.example/foto.jpg")

    def test_rejects_video_and_insecure_images(self):
        node = ET.fromstring('''<item xmlns:media="http://search.yahoo.com/mrss/">
          <media:content medium="video" url="https://editor.example/video.mp4"/>
          <media:thumbnail url="http://editor.example/foto.jpg"/>
          <enclosure type="image/jpeg" url="https://editor.example/alternativa.jpg"/>
        </item>''')
        self.assertEqual(news.rss_image(node), "https://editor.example/alternativa.jpg")

    def test_keeps_direct_media_content_photo(self):
        node = ET.fromstring('''<item xmlns:media="http://search.yahoo.com/mrss/">
          <media:content medium="image" url="https://editor.example/directa.webp"/>
        </item>''')
        self.assertEqual(news.rss_image(node), "https://editor.example/directa.webp")

    def test_no_image_does_not_invent_photo(self):
        node = ET.fromstring('<item><title>Sin foto</title></item>')
        self.assertEqual(news.rss_image(node), "")


if __name__ == "__main__":
    unittest.main()
