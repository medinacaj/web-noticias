import unittest


class ReadingTopicsTests(unittest.TestCase):
    def test_economy_topics_require_a_specific_signal(self):
        from scripts.reading_topics import story_topics, topic_choices
        startup = {'category':'economia','title':'Startup chilena cierra ronda de inversión'}
        jobs = {'category':'economia','title':'Nueva ley de empleo y sueldos'}
        self.assertIn('startups', story_topics(startup))
        self.assertNotIn('startups', story_topics(jobs))
        self.assertNotIn('startups', story_topics({**startup,'category':'deportes'}))
        self.assertEqual(topic_choices([startup,jobs], 'economia'), [('','Todos'),('startups','Startups e inversión'),('empleo','Empleo')])

    def test_group_filters_keep_original_subtopics(self):
        from scripts.reading_topics import topic_choices
        items = [{'category':c,'title':'Información'} for c in ('politica','regiones','nacional')]
        self.assertEqual(topic_choices(items, 'nacional'), [('','Todos'),('nacional','Nacional'),('politica','Política'),('regiones','Regiones')])

    def test_cinema_distinguishes_verified_formats_from_announcements(self):
        from scripts.reading_topics import story_topics
        news = {'category':'cine-streaming','content_kind':'premiere-news','title':'Netflix estrenará una película'}
        verified = {**news,'content_kind':'premiere','format':'Streaming','region':'CL','platform':'Netflix'}
        self.assertNotIn('streaming',story_topics(news))
        self.assertIn('streaming',story_topics(verified))
        self.assertIn('anuncios',story_topics(news))

    def test_single_unfiltered_category_needs_no_redundant_controls(self):
        from scripts.reading_topics import topic_choices
        self.assertEqual(topic_choices([{'category':'deportes','title':'Tenis'}], 'deportes'), [])
