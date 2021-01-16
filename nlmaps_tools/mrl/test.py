# -*- coding: utf-8 -*-
"""Contains tests for the MRL class in mrl.py"""

import os
import unittest

from . import local_io
from . import mrl
from . import CFG_DIR


class MRLTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.nlmaps_world = mrl.MRLS['nlmaps']()
        cls.nlmaps_train_lin = os.environ.get('NLMAPS_TRAIN_LIN')
        cls.nlmaps_train_mrl = os.environ.get('NLMAPS_TRAIN_MRL')
        cls.nlmaps_dev_lin = os.environ.get('NLMAPS_DEV_LIN')
        cls.nlmaps_dev_mrl = os.environ.get('NLMAPS_DEV_MRL')
        cls.nlmaps_test_lin = os.environ.get('NLMAPS_TEST_LIN')
        cls.nlmaps_test_mrl = os.environ.get('NLMAPS_TEST_MRL')
        cls.cfg = os.path.join(CFG_DIR, 'nlmaps')

    def test_functionalise_from_nlmaps(self):
        # generic tests
        test_reponse = self.nlmaps_world.functionalise("query@3 area@2 keyval@2 name@0 Paris@s keyval@2 is_in:country@0 France@s nwr@1 keyval@2 cuisine@0 japanese@s qtype@1 count@0")
        goal = "query(area(keyval('name','Paris'),keyval('is_in:country','France')),nwr(keyval('cuisine','japanese')),qtype(count))"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        test_reponse = self.nlmaps_world.functionalise("query@3 area@2 keyval@2 name@0 Heidelberg@s keyval@2 de:place@0 city@s nwr@1 keyval@2 name@0 McDonaldSAVEAPOs@s qtype@1 count@0")
        goal = "query(area(keyval('name','Heidelberg'),keyval('de:place','city')),nwr(keyval('name','McDonald's')),qtype(count))"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        test_reponse = self.nlmaps_world.functionalise("query@3 area@2 keyval@2 name@0 Heidelberg@s keyval@2 de:place@0 city@s nwr@1 keyval@2 name@0 MBRACKETOPENcBRACKETCLOSEDonalds@s qtype@1 count@0")
        goal = "query(area(keyval('name','Heidelberg'),keyval('de:place','city')),nwr(keyval('name','M(c)Donalds')),qtype(count))"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        test_reponse = self.nlmaps_world.functionalise("query@3 area@2 keyval@2 name@0 Heidelberg@s keyval@2 de:place@0 city@s nwr@1 keyval@2 name@0 Mc€Donalds@s qtype@1 count@0")
        goal = "query(area(keyval('name','Heidelberg'),keyval('de:place','city')),nwr(keyval('name','Mc Donalds')),qtype(count))"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        test_reponse = self.nlmaps_world.functionalise("query@3 area@2 keyval@2 name@0 Paris@s keyval@2 is_in:country@0 France@s nwr@1 keyval@2 cuisine@0 japaneseSAVECOMMAitalian@s qtype@1 count@0")
        goal = "query(area(keyval('name','Paris'),keyval('is_in:country','France')),nwr(keyval('cuisine','japanese,italian')),qtype(count))"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        test_reponse = self.nlmaps_world.functionalise("query@2 around@4 center@2 area@2 keyval@2 name@0 Heidelberg@s keyval@2 de:place@0 city@s nwr@1 keyval@2 name@0 Yorckstra\xdfe@s search@1 nwr@1 and@2 keyval@2 amenity@0 bank@s keyval@2 amenity@0 pharmacy@s maxdist@1 DIST_INTOWN@0 topx@1 1@0 qtype@1 latlong@0")
        goal = "query(around(center(area(keyval('name','Heidelberg'),keyval('de:place','city')),nwr(keyval('name','Yorckstraße'))),search(nwr(and(keyval('amenity','bank'),keyval('amenity','pharmacy')))),maxdist(DIST_INTOWN),topx(1)),qtype(latlong))"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        test_reponse = self.nlmaps_world.functionalise("query@3 area@2 keyval@2 name@0 Paris@s keyval@2 is_in:country@0 France@s nwr@2 keyval@2 amenity@0 restaurant@s keyval@2 cuisine@0 or@2 greek@s italian@s qtype@1 count@0")
        goal = "query(area(keyval('name','Paris'),keyval('is_in:country','France')),nwr(keyval('amenity','restaurant'),keyval('cuisine',or('greek','italian'))),qtype(count))"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        # test pass through
        test_reponse = self.nlmaps_world.functionalise("query@3 area@2 keyval@2 name@0 pari keyval@2 is_in:country@0 France@s nwr@1 keyval@2 cuisine@0 japanese@s qtype@1 count@0", non_stemmed = "noise noise Paris noise", stemmed = "noise noise pari noise")
        goal = "query(area(keyval('name','Paris'),keyval('is_in:country','France')),nwr(keyval('cuisine','japanese')),qtype(count))"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        # test CFG
        test_reponse = self.nlmaps_world.functionalise("query@3 area@2 keyval@2 name@0 Paris@s keyval@2 is_in:country@0 France@s nwr@1 keyval@2 cuisine@0 japanese@s qtype@1 count@0", cfg = self.cfg)
        goal = "query(area(keyval('name','Paris'),keyval('is_in:country','France')),nwr(keyval('cuisine','japanese')),qtype(count))"
        #self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        test_reponse = self.nlmaps_world.functionalise("query@3 area@2 failval@2 name@0 Paris@s keyval@2 is_in:country@0 France@s nwr@1 keyval@2 cuisine@0 japanese@s qtype@1 count@0", cfg = self.cfg)
        goal = ""
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        # test to ensure that wrong MRLs actually do fail
        test_reponse = self.nlmaps_world.functionalise("query@5 area@2 keyval@2 name@0 Paris@s keyval@2 is_in:country@0 France@s nwr@1 keyval@2 cuisine@0 japanese@s qtype@1 count@0")
        goal = ""
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        # test whole nlmaps
        if self.nlmaps_train_lin and self.nlmaps_train_mrl:
            input = local_io.read_lines_in_list(self.nlmaps_train_lin)
            goal = local_io.read_lines_in_list(self.nlmaps_train_mrl)
            for i, line in enumerate(input):
                line_preprocessed = self.nlmaps_world.functionalise(line)
                self.assertEqual(line_preprocessed, goal[i], "These are not the same:\noutput: %s\ngoal: %s" % (line_preprocessed, goal[i]))
        if self.nlmaps_dev_lin and self.nlmaps_dev_mrl:
            input = local_io.read_lines_in_list(self.nlmaps_dev_lin)
            goal = local_io.read_lines_in_list(self.nlmaps_dev_mrl)
            for i, line in enumerate(input):
                line_preprocessed = self.nlmaps_world.functionalise(line)
                self.assertEqual(line_preprocessed, goal[i], "These are not the same:\noutput: %s\ngoal: %s" % (line_preprocessed, goal[i]))
        if self.nlmaps_test_lin and self.nlmaps_test_mrl:
            input = local_io.read_lines_in_list(self.nlmaps_dev_lin)
            goal = local_io.read_lines_in_list(self.nlmaps_dev_mrl)
            for i, line in enumerate(input):
                line_preprocessed = self.nlmaps_world.functionalise(line)
                self.assertEqual(line_preprocessed, goal[i], "These are not the same:\noutput: %s\ngoal: %s" % (line_preprocessed, goal[i]))

    def test_preprocess_mrl_from_nlmaps(self):
        test_reponse = self.nlmaps_world.preprocess_mrl("query(area(keyval('name','Paris'),keyval('is_in:country','France')),nwr(keyval('cuisine','japanese')),qtype(count))")
        goal = "query@3 area@2 keyval@2 name@0 Paris@s keyval@2 is_in:country@0 France@s nwr@1 keyval@2 cuisine@0 japanese@s qtype@1 count@0"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        test_reponse = self.nlmaps_world.preprocess_mrl("query(area(keyval('name','Heidelberg'),keyval('de:place','city')),nwr(keyval('name','McDonald's')),qtype(count))")
        goal = "query@3 area@2 keyval@2 name@0 Heidelberg@s keyval@2 de:place@0 city@s nwr@1 keyval@2 name@0 McDonaldSAVEAPOs@s qtype@1 count@0"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        test_reponse = self.nlmaps_world.preprocess_mrl("query(area(keyval('name','Heidelberg'),keyval('de:place','city')),nwr(keyval('name','M(c)Donalds')),qtype(count))")
        goal = "query@3 area@2 keyval@2 name@0 Heidelberg@s keyval@2 de:place@0 city@s nwr@1 keyval@2 name@0 MBRACKETOPENcBRACKETCLOSEDonalds@s qtype@1 count@0"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        test_reponse = self.nlmaps_world.preprocess_mrl("query(area(keyval('name','Heidelberg'),keyval('de:place','city')),nwr(keyval('name','Mc Donalds')),qtype(count))")
        goal = "query@3 area@2 keyval@2 name@0 Heidelberg@s keyval@2 de:place@0 city@s nwr@1 keyval@2 name@0 Mc€Donalds@s qtype@1 count@0"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        test_reponse = self.nlmaps_world.preprocess_mrl("query(area(keyval('name','Paris'),keyval('is_in:country','France')),nwr(keyval('cuisine','japanese,italian')),qtype(count))")
        goal = "query@3 area@2 keyval@2 name@0 Paris@s keyval@2 is_in:country@0 France@s nwr@1 keyval@2 cuisine@0 japaneseSAVECOMMAitalian@s qtype@1 count@0"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        test_reponse = self.nlmaps_world.preprocess_mrl("query(around(center(area(keyval('name','Heidelberg'),keyval('de:place','city')),nwr(keyval('name','Yorckstraße'))),search(nwr(and(keyval('amenity','bank'),keyval('amenity','pharmacy')))),maxdist(DIST_INTOWN),topx(1)),qtype(latlong))")
        goal = "query@2 around@4 center@2 area@2 keyval@2 name@0 Heidelberg@s keyval@2 de:place@0 city@s nwr@1 keyval@2 name@0 Yorckstraße@s search@1 nwr@1 and@2 keyval@2 amenity@0 bank@s keyval@2 amenity@0 pharmacy@s maxdist@1 DIST_INTOWN@0 topx@1 1@0 qtype@1 latlong@0"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        test_reponse = self.nlmaps_world.preprocess_mrl("query(area(keyval('name','Paris'),keyval('is_in:country','France')),nwr(keyval('amenity','restaurant'),keyval('cuisine',or('greek','italian'))),qtype(count))")
        goal = "query@3 area@2 keyval@2 name@0 Paris@s keyval@2 is_in:country@0 France@s nwr@2 keyval@2 amenity@0 restaurant@s keyval@2 cuisine@0 or@2 greek@s italian@s qtype@1 count@0"
        self.assertEqual(test_reponse, goal, "These are not the same:\noutput: %s\ngoal: %s" % (test_reponse, goal))
        # test whole nlmaps
        if self.nlmaps_train_lin and self.nlmaps_train_mrl:
            input = local_io.read_lines_in_list(self.nlmaps_train_mrl)
            goal = local_io.read_lines_in_list(self.nlmaps_train_lin)
            for i, line in enumerate(input):
                line_preprocessed = self.nlmaps_world.preprocess_mrl(line)
                self.assertEqual(line_preprocessed, goal[i], "These are not the same:\noutput: %s\ngoal: %s" % (line_preprocessed, goal[i]))
        if self.nlmaps_dev_lin and self.nlmaps_dev_mrl:
            input = local_io.read_lines_in_list(self.nlmaps_dev_mrl)
            goal = local_io.read_lines_in_list(self.nlmaps_dev_lin)
            for i, line in enumerate(input):
                line_preprocessed = self.nlmaps_world.preprocess_mrl(line)
                self.assertEqual(line_preprocessed, goal[i], "These are not the same:\noutput: %s\ngoal: %s" % (line_preprocessed, goal[i]))
        if self.nlmaps_test_lin and self.nlmaps_test_mrl:
            input = local_io.read_lines_in_list(self.nlmaps_test_mrl)
            goal = local_io.read_lines_in_list(self.nlmaps_test_lin)
            for i, line in enumerate(input):
                line_preprocessed = self.nlmaps_world.preprocess_mrl(line)
                self.assertEqual(line_preprocessed, goal[i], "These are not the same:\noutput: %s\ngoal: %s" % (line_preprocessed, goal[i]))


def main():
    unittest.main()


if __name__ == '__main__':
    main()
