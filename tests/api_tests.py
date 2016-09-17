#!/usr/bin/env python
import os
import unittest
import tempfile
import json
from time import sleep
from StringIO import StringIO

import poli
from poli.controllers.api import APIControl


class ApiTestCase(unittest.TestCase):
    """
        Tests cases for the API endpoints
    """
    def setUp(self):
        self.db_fd, self.fname = tempfile.mkstemp()
        poli.app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///"+self.fname
        poli.app.config['TESTING'] = False
        poli.app.config['WTF_CSRF_ENABLED'] = False
        self.app = poli.app.test_client()
        poli.db.create_all()
        with poli.app.app_context():
            api = APIControl()
            api.usercontrol.create("john", "password")
        self.create_sample()
        poli.db.session.commit()

    def tearDown(self):
        poli.db.session.remove()
        poli.db.drop_all()
        os.close(self.db_fd)
        os.unlink(self.fname)

    def login(self, username, password):
        return self.app.post("/login/",
                             data=dict(
                                 username=username,
                                 password=password),
                             follow_redirects=True)

    def create_sample(self):
        with open("tests/example_pe.bin", "rb") as hfile:
            data = StringIO(hfile.read())
        self.login("john", "password")
        retval = self.app.post("/samples/",
                               content_type='multipart/form-data',
                               data=dict({'file': (data, "toto")},
                                         level=1, family=0),
                               follow_redirects=True)
        sleep(2)
        return retval

    def push_comment(self, sid=1, address=None, comment=None):
        retval = self.app.post('/api/1.0/samples/'+str(sid)+'/comments/',
                               data=json.dumps(dict(address=address, comment=comment)),
                               content_type="application/json")
        return retval


    def create_struct(self, sid=1, name=None):
        retval = self.app.post('/api/1.0/samples/'+str(sid)+'/structs/',
                            data=json.dumps(dict(name=name)),
                            content_type="application/json")
        return retval

    def create_struct_member(self, sid=1, struct_id=None, mname=None, size=0, offset=0):
        url = '/api/1.0/samples/' + str(sid)
        url += '/structs/' + str(struct_id)
        url += '/members/'
        retval = self.app.post(url,
                            data=json.dumps(dict(name=mname,
                                                size=size,
                                                offset=offset)),
                            content_type="application/json")
        return retval

    def update_struct_member(self, sid=1, struct_id=None, mname=None, size=0, offset=0):
        url = '/api/1.0/samples/' + str(sid)
        url += '/structs/' + str(struct_id)
        url += '/members/' + str(mid) + '/'
        retval = self.app.patch(url,
                            data=json.dumps(dict(mname=mname,
                                                size=size,
                                                offset=offset)),
                            content_type="application/json")
        return retval


    def get_all_structs(self, sid=1, name=None):
        retval = self.app.get('/api/1.0/samples/' + str(sid) +
                              '/structs/')
        return retval

    def get_one_struct(self, sid=1, struct_id=1):
        url = '/api/1.0/samples/' + str(sid)
        url += '/structs/'
        url += str(struct_id) + '/'
        retval = self.app.get(url)
        return retval


    def get_comment(self, sid=1, address=None):
        retval = self.app.get('/api/1.0/samples/' + str(sid) +
                              '/comments/',
                              data=json.dumps({'address':address}),
                              content_type="application/json")
        return retval

    def push_name(self, sid=1, address=None, name=None):
        retval = self.app.post('/api/1.0/samples/'+str(sid)+'/names/',
                               data=json.dumps(dict(address=address, name=name)),
                               content_type="application/json")
        return retval

    def get_name(self, sid=1, address=None):
        retval = self.app.get('/api/1.0/samples/' + str(sid) +
                              '/names/')
        return retval

    def test_get_sample_info(self):
        """
            Just check if we can access the sample id
        """
        retval = self.app.get('/api/1.0/samples/1/')
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertEqual(len(data),1)
        data = data['samples']
        self.assertEqual(data['id'], 1)

    def test_get_sample_id(self):
        # test getting ID by MD5
        retval = self.app.get('/api/1.0/samples/0f6f0c6b818f072a7a6f02441d00ac69/')
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertEqual(data['sample_id'], 1)

        # get ID by SHA1
        retval = self.app.get('/api/1.0/samples/39b8a7a0a99f6e2220cf60fd860923f9df3e8d01/')
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertEqual(data['sample_id'], 1)

        # get ID by SHA256
        retval = self.app.get('/api/1.0/samples/e5b830bf3d82aba009244bff86d33b10a48b03f48ca52cd1d835f033e2b445e6/')
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertEqual(data['sample_id'], 1)

        # Bug when using incorrect value for hash
        url = "api/1.0/samples/abcdef/"
        retval = self.app.get(url)
        self.assertEqual(retval.status_code, 400)
        data = json.loads(retval.data)
        self.assertEqual(data['error'], 400)

    def test_get_multiples_sample_info(self):
        retval = self.app.get('/api/1.0/samples/')
        self.assertEqual(retval.status_code, 200)

        data = json.loads(retval.data)
        self.assertEqual(len(data['samples']), 1)

        self.assertEqual(data['samples'][0]['md5'],
                         '0f6f0c6b818f072a7a6f02441d00ac69')

        self.assertEqual(data['samples'][0]['sha1'],
                         '39b8a7a0a99f6e2220cf60fd860923f9df3e8d01')

        self.assertEqual(data['samples'][0]['sha256'],
                         'e5b830bf3d82aba009244bff86d33b10a48b03f48ca52cd1d835f033e2b445e6')

        self.assertEqual(data['samples'][0]['size'], 12361)

    def test_get_analysis_data(self):
        retval = self.app.get('/api/1.0/samples/1/analysis/')
        self.assertEqual(retval.status_code, 200)

        data = json.loads(retval.data)

        self.assertIn('analysis', data.keys())

    def test_get_analyzeit_data(self):
        retval = self.app.get('/api/1.0/samples/1/analysis/analyzeit/')
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertEqual(len(data), 1)

    def test_get_peinfo_data(self):
        retval = self.app.get('/api/1.0/samples/1/analysis/peinfo/')
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertEqual(len(data), 1)

    def test_get_strings_data(self):
        retval = self.app.get('/api/1.0/samples/1/analysis/strings/')
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertEqual(len(data), 1)

    def test_push_comments(self):
        retval = self.push_comment(address=0xDEADBEEF, comment="TESTCOMMENT1")
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertTrue(data['result'])

    def test_get_comment(self):
        """
            This endpoint is used to get comments for a specific address
        """
        retval = self.push_comment(address=0xDEADBEEF, comment="TESTCOMMENT1")
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertTrue(data['result'])

        retval = self.get_comment(address=0xDEADBEEF)
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertIn(data['comments'][0]["data"], "TESTCOMMENT1")
        self.assertEqual(data['comments'][0]["address"], 0xDEADBEEF)

    def test_get_multiple_comments(self):
        retval = self.push_comment(address=0xDEADBEEF, comment="TESTCOMMENT1")
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertTrue(data['result'])

        retval = self.push_comment(address=0xBADF00D, comment="TESTCOMMENT2")
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertTrue(data['result'])

        retval = self.get_comment()
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertEqual(len(data['comments']), 2)
        self.assertIn(data['comments'][0]["data"], "TESTCOMMENT1")
        self.assertEqual(data['comments'][0]["address"], 0xDEADBEEF)
        self.assertIn(data['comments'][1]["data"], "TESTCOMMENT2")
        self.assertEqual(data['comments'][1]["address"], 0xBADF00D)

    def test_push_name(self):
        """
            Simulate a renaming done from IDA
        """
        retval = self.push_name(address=0xDEADBEEF, name="TESTNAME1")
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertTrue(data['result'])

    def test_get_names(self):
        """
            This endpoint is used to get names for a specific address
        """
        retval = self.push_name(address=0xDEADBEEF, name="TESTNAME1")
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertTrue(data['result'])

        retval = self.get_name(address=0xDEADBEEF)
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertIn(data['names'][0]["data"], "TESTNAME1")
        self.assertEqual(data['names'][0]["address"], 0xDEADBEEF)

    def test_create_struct(self):
        """
            Simple structure creation and access
        """
        retval = self.create_struct(sid=1, name="StructName1")
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertTrue(data["result"])

        # check if the structure is in the complete listing
        retval = self.get_all_structs(sid=1)
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertIn("StructName1", data["structs"][0]["name"])
        self.assertEqual(0, data["structs"][0]["size"])

        # check if we can access the structure alone
        retval = self.get_one_struct(sid=1, struct_id=1)
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        struct = data["structs"]
        self.assertIn("StructName1", struct["name"])
        self.assertEqual(0, struct["size"])

    def test_create_multiple_structs(self):
        """
            This will test if we can access multiple structs for one sample
        """
        # create structs
        retval = self.create_struct(sid=1, name="StructName1")
        data = json.loads(retval.data)
        self.assertTrue(data["result"])

        retval = self.create_struct(sid=1, name="StructName2")
        data = json.loads(retval.data)
        self.assertTrue(data["result"])

        # get the structs
        retval = self.get_all_structs(sid=1)
        data = json.loads(retval.data)
        self.assertEqual(2, len(data["structs"]))
        struct1 = data["structs"][0]
        struct2 = data["structs"][1]
        self.assertIn("StructName1", struct1["name"])
        self.assertIn("StructName2", struct2["name"])
        self.assertEqual(0, struct1["size"])
        self.assertEqual(0, struct2["size"])



    def test_create_struct_member(self):
        """
            Member creation
        """
        # first create a structre
        self.create_struct(sid=1, name="StructName1")
        # then add a member to it
        retval = self.create_struct_member(struct_id=1,
                mname="MemberName1",
                size=4,
                offset=0)
        # Is the member OK?
        self.assertEqual(retval.status_code, 200)
        data = json.loads(retval.data)
        self.assertTrue(data["result"])

        # can we get the member in the structure
        retval = self.get_one_struct(sid=1, struct_id=1)
        data = json.loads(retval.data)
        struct = data["structs"]

        self.assertEqual(len(struct["members"]), 1)
        self.assertEqual(struct["size"], 4)
        member = struct["members"][0]
        self.assertIn("MemberName1", member["name"])
        self.assertEqual(4, member["size"])
        self.assertEqual(0, member["offset"])


if __name__ == '__main__':
    unittest.main()
