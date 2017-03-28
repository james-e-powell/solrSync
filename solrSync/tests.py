from datetime import datetime

from django.test import TestCase

from solrSync.models import ResourceSync

class ResourceListTest(TestCase):

  def test_str(self):
    # thisMoment = '"{:%Y-%m-%d %H:%M:%SZ}"'.format(datetime.datetime.now())

    # resourceList = ResourceSync(list_type='resourcelist')
    # resourcelist_timestamp = str(resourceList.list_date)
    # print resourcelist_timestamp
    # solr_timestamp = '"{:%Y-%m-%dT%H:%M:%S}"'.format(resourcelist_timestamp)

    thisMoment = datetime.now()
    print 'now value: ' + str(thisMoment)
    aResourceSyncEntry = ResourceSync(list_date = thisMoment)
    aResourceSyncEntry.list_type='resourcelist'
    print 'ResourceSync model list date value: ' + str(aResourceSyncEntry.list_date)
    print 'ResourceSync model list type value: ' + str(aResourceSyncEntry.list_type)
    print 'formatted for solr: "{:%Y-%m-%dT%H:%M:%SZ}"'.format(thisMoment)

    self.assertEquals(str(aResourceSyncEntry.list_date), str(thisMoment))
