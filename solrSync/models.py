from django.db import models

from django.utils import timezone
import sys
import re
import string
import xmltodict
import requests
from django.conf import settings
import django.conf as conf
import datetime
import time

class ResourceSync(models.Model):
  # lower_bound is a value for changelists
  lower_bound = models.DateTimeField(blank=True, null=True)
  list_type = models.CharField(max_length=255)
  interval = models.DurationField(default = datetime.timedelta(days=5), blank=True, null=True)

class ResultsQuerySet(models.QuerySet):
  def results(self):
    return self.resultSet

class ResultsManager(models.Manager):
    app_label='ResultsManager'

    # def get_queryset(self):
    #   return Results(self.model, using=self.results)

    def headUri(resourceUri):
      resp = requests.head(resourceUri)
      metadata = {}
      metadata['Content-Length'] = resp.headers['Content-Length']
      metadata['Content-Type'] = resp.headers['Content-Type']
      return metadata

    def getUri(resourceUri):
      resp = requests.get(resourceUri)
      return resp.text

    # def results(self, resourceSyncType, timestamp):
    def get_queryset(self, numResults):
      # returns a list of resultObj
      # resultObj has following fields: recID, timestamp, doi, contentUri
      # resultObj is build from Solr results set doc entries

      resultSet = []
      # Constants
      metadataUriBase = 'http://lastage.lanl.gov:8080/adore-disseminator/service?url_ver=Z39.88-2004&rft_id=_URI_&svc_id=info:lanl-repo/svc/xml.format.full'
      doiResolver = 'https://dx.doi.org/'
      permalinkReports = 'http://permalink.lanl.gov/object/tr?what=info:lanl-repo/lareport/'
      solrUriBase = 'http://hydraweb.lanl.gov:8080/solr/laro/select?q=_FIELD_%3A_QUERY_&wt=xml&indent=true&sort=recID+asc&cursorMark=*'
      solrCollUriBase = 'http://hydraweb.lanl.gov:8080/solr/laro/select?q=collection_f:%22_COLLECTION_%22&sort=timestamp+asc&wt=xml&indent=true&cursorMark=*'
      docBaseUri = 'http://permalink.lanl.gov/object/tr?what=_ID_'

      queryField = 'title'
      queryString = settings.RESOURCESYNC_QUERY
      # timestamp = settings.RESOURCESYNC_RESOURCELIST_TIMESTAMP
      solr_timestamp = ''
      thisMoment = timezone.now()
  
      resourcelist_timestamp = thisMoment

      solr_timestamp = settings.RESOURCESYNC_RESOURCELIST_TIMESTAMP
      print solr_timestamp

      count=0
      recFound = False
      urlFound = False
      allFound = False
      pagingCursor = ''

      while not(allFound):
        count += 1
        lastCursor = pagingCursor
        if count>=numResults:
          allFound = True

        searchUri = settings.RESOURCESYNC_SOLR
        try:
          searchUri = searchUri.replace('_FIELD_', queryField)
        except:
          pass
        try:
          searchUri = searchUri.replace('_QUERY_', queryString)
        except:
          pass
        searchUri = searchUri.replace('_TIMESTAMP_', solr_timestamp)

        if not (pagingCursor == ''):
          searchUri = searchUri.replace('_*_',pagingCursor)
        else:
          searchUri = searchUri.replace('_*_','*')

        resp = requests.get(searchUri)
        r = resp.text

        # r = getUri(searchUri)

        xmldict = xmltodict.parse(r)
        try:
          pagingCursorMark = xmldict['response']['str']['@name']

          if pagingCursorMark == 'nextCursorMark':
            pagingCursor =  xmldict['response']['str']['#text']
        except:
          pagingCursor = lastCursor

        if pagingCursor == lastCursor:
          allFound = True
        else:
          try: 
            docNodes = []
            docNodes = xmldict['response']['result']['doc']
            for docNode in docNodes:
              resultObj = {}
              docStringNodes = []
              docStringNodes = docNode['str']
              arrStringNodes = []
              arrStringNodes = docNode['arr']
              timestamp = docNode['date']['#text']
              resultObj['timestamp'] = timestamp
              print resultObj['timestamp']
              doi = ''
              recId = ''
              for docStringNode in docStringNodes:
                name = docStringNode['@name']
                if name == 'recID':
                  recId = docStringNode['#text']
                  resultObj['recID'] = recId
                  recFound = True
                  count+=1
                if name == 'doi' and recFound:
                  doi = docStringNode['#text']
                  resultObj['doi'] = doi

              recMetadataUri =  metadataUriBase.replace('_URI_', recId)
              print recMetadataUri
              print str(count)
              resourceWritten = False

              for arrStringNode in arrStringNodes:
                name = arrStringNode['@name']
                print name
                if name == 'url':
                  linklStringNodes = []
                  linkStringNodes = arrStringNode['str']
                  linkText = linkStringNodes
                  print linkText
                  if '|' in linkText:
                    linkTextParts = linkText.split('|')
                    linkLabel = linkTextParts[0]
                    linkVal = linkTextParts[1]
                    print 'linkval = ' +linkVal
                    resultObj['contentUri']= linkVal
     
                    try:
                      thisResource = Resource(uri=linkVal, lastmod = timestamp)
                      thisResource.link_set(rel="describedby", modified = timestamp, href = recMetadataUri)
                      print ' got this far '
                      thisResourceRecip = Resource(uri = recMetadataUri, lastmod = timestamp)
                      thisResourceRecip.link_set(rel="describes", href=linkVal, modified=timestamp)
                      thisResourceRecip.link_set(rel="profile", href="http://www.w3.org/2001/XMLSchema-instance")
                      resourceWritten = True
                      print 'resource added for ' + linkVal
                    except Exception as e: print str(e)

              resultSet.append(resultObj)
              if not resourceWritten: 
                thisResource = Resource(uri=recMetadataUri, lastmod = timestamp, mime_type="application/xml", )
                thisResource.link_set(rel="profile", href="http://www.w3.org/2001/XMLSchema-instance")
            if count>=numResults:
              allFound = True
          except:
            pass

      print resultSet
      return resultSet

class Results(models.Model):
    app_label='Results'
    results = ResultsManager()

