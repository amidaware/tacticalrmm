from tacticalrmm.test import TacticalTestCase


class TestWinUpdateViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()
