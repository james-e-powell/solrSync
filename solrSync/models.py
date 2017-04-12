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
    # This class extracts information from a Solr results set
    # It is specifically looking for timestamp, metadata URI, full text
    #   At LANL there's a common repository (aDORe), so recID is used 
    #     to construct a URI that points at metadata, this is found in a str 
    #     element with a name attribute assigned the value "recID"
    #   Full text is found in a arr element with a name element with value "url"
    #     sometimes there are multiple full text uris separated by "| character
    #   timestamp is in the date element
    #   DOI is found in a str element, name attribute assigned the value "doi"
    # The list contains an entry per Solr doc element in results 
    # The result list entries format is described below 

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

    # def get_queryset(self, numResults):
    def get_queryset(self, listTimestamp):
      # returns a list of resultObj
      # resultObj has following fields: recID, timestamp, doi, contentUri
      # resultObj is build from Solr results set doc entries

      resultSet = []
      # Constants
      metadataUriBase = settings.METADATAURIBASE

  
      # solr_timestamp = settings.RESOURCESYNC_RESOURCELIST_TIMESTAMP
      solr_timestamp = listTimestamp

      count=0
      recFound = False
      urlFound = False
      allFound = False
      pagingCursor = ''

      while not(allFound):
        count += 1
        lastCursor = pagingCursor

        searchUri = settings.RESOURCESYNC_SOLR
        searchUri = searchUri.replace('_TIMESTAMP_', solr_timestamp)
        print searchUri

        if not (pagingCursor == ''):
          searchUri = searchUri.replace('_*_',pagingCursor)
        else:
          searchUri = searchUri.replace('_*_','*')

        resp = requests.get(searchUri)
        r = resp.text

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
              print str(count)

              for arrStringNode in arrStringNodes:
                name = arrStringNode['@name']
                if name == 'url':
                  linklStringNodes = []
                  linkStringNodes = arrStringNode['str']
                  linkText = linkStringNodes
                  if '|' in linkText:
                    linkTextParts = linkText.split('|')
                    linkLabel = linkTextParts[0]
                    linkVal = linkTextParts[1]
                    resultObj['contentUri']= linkVal
              try:
                # test = resultObj['contentUri'] 
                resultSet.append(resultObj)
              except:
                pass
          except:
            pass

      return resultSet

class Results(models.Model):
    app_label='Results'
    results = ResultsManager()

