from django.utils import timezone
import models
import sys
import re
import string
import xmltodict
import requests
from django.http import HttpResponse, StreamingHttpResponse
from django.conf import settings
import django.conf as conf
import datetime
import time
from django.views.decorators.http import condition
from resync import Resource,ResourceList,ChangeList

# Constants
metadataUriBase = 'http://lastage.lanl.gov:8080/adore-disseminator/service?url_ver=Z39.88-2004&rft_id=_URI_&svc_id=info:lanl-repo/svc/xml.format.full'
doiResolver = 'https://dx.doi.org/'
permalinkReports = 'http://permalink.lanl.gov/object/tr?what=info:lanl-repo/lareport/'
solrUriBase = 'http://hydraweb.lanl.gov:8080/solr/laro/select?q=_FIELD_%3A_QUERY_&wt=xml&indent=true&sort=recID+asc&cursorMark=*'
solrCollUriBase = 'http://hydraweb.lanl.gov:8080/solr/laro/select?q=collection_f:%22_COLLECTION_%22&sort=timestamp+asc&wt=xml&indent=true&cursorMark=*'
docBaseUri = 'http://permalink.lanl.gov/object/tr?what=_ID_'

@condition(etag_func=None)
def stream_response(request):
    return StreamingHttpResponse(stream_response_generator())

def stream_response_generator():
 yield "<html><body>\n"
 for x in range(1,11):
      yield "<div>%s</div>\n" % x
      yield " " * 1024  # Encourage browser to render incrementally
      time.sleep(1)
 yield "</body></html>\n"

def headUri(resourceUri):
  resp = requests.head(resourceUri)
  # print resp.status_code, resp.text, resp.headers
  metadata = {}
  # print resp.headers['Content-Length']
  metadata['Content-Length'] = resp.headers['Content-Length']
  # print resp.headers['Content-Type']
  metadata['Content-Type'] = resp.headers['Content-Type']
  return metadata

def getUri(resourceUri):
  resp = requests.get(resourceUri)
  # print resp.status_code, resp.text, resp.headers
  # print resp.text
  return resp.text

def resourceSync(response):
  response = HttpResponse()
  response.write('<html><head><title>Resource Sync settings</title></head>')
  response.write('<body>')
  response.write('<h3>Contents of resourcesync sqllite table</h3>')
  response.write('<table border="1">')
  response.write('<tr><th>list type</th><th>list date</th><th>interval</th></tr>')
  rowSet = models.ResourceSync.objects.all()
  for entry in rowSet.iterator():
    response.write('<tr><td>' + entry.list_type + '</td>')
    response.write('<td>' + str(entry.lower_bound) + '</td>')
    response.write('<td>' + str(entry.interval) + '</td></tr>')
  response.write('</table><p>')
  response.write('Excerpt from django settings file: <p>')
  response.write('# ResourceSync Application settings <br>')
  response.write('RESOURCESYNC_SOLR = http://hydraweb.lanl.gov:8080/solr/laro/select?q=_FIELD_%3A_QUERY_%20AND%20timestamp:[*%20TO%20_TIMESTAMP_]&wt=xml&indent=true&sort=recID+asc&cursorMark=_*_<br>')
  response.write('RESOURCESYNC_QUERY = chem*<br>')
  response.write('RESOURCESYNC_RESOURCELIST_TIMESTAMP=2016-01-30T16:33:33Z<br>')
  response.write('RESOURCESYNC_CHANGELIST_TIMESTAMP=2016-05-26T16:33:33Z<br>')
  response.write('RESOURCESYNC_CHANGELIST_INTERVAL = 8 hours<br>')
  response.flush()
  
  return response

def dbLookup(list_type):
  try:
    resourceSync = models.ResourceSync.objects.get(list_type=list_type)
  except:
    thisMoment = timezone.now()
    resourceSync = models.ResourceSync(lower_bound = thisMoment, list_type=list_type, interval=None)
    resourceSync.save()
  return resourceSync

def resourcelist(response):
  response = HttpResponse()
  response.writable()

  rl = ResourceList()

  queryField = 'title'
  queryString = settings.RESOURCESYNC_QUERY
  # timestamp = settings.RESOURCESYNC_RESOURCELIST_TIMESTAMP
  solr_timestamp = ''
  
  rl.up = "capabilitylist.xml"

  resourceList = dbLookup('resourcelist')
  resourcelist_refresh = resourceList.interval
  resourcelist_timestamp = resourceList.lower_bound
  print 'resourcelist timestamp: ' + resourcelist_timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
  solr_timestamp = resourcelist_timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')

  print 'solr timestamp: ' + solr_timestamp
  rl.md_until = resourcelist_timestamp

  count=0
  recFound = False
  urlFound = False
  allFound = False
  pagingCursor = ''
  print allFound

  while not(allFound):
    lastCursor = pagingCursor

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
    print searchUri

    if not (pagingCursor == ''):
      searchUri = searchUri.replace('_*_',pagingCursor)
    else:
      searchUri = searchUri.replace('_*_','*')

    r = getUri(searchUri)

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

          docStringNodes = []
          docStringNodes = docNode['str']
          arrStringNodes = []
          arrStringNodes = docNode['arr']
          timestamp = docNode['date']['#text']
          doi = ''
          recId = ''
          for docStringNode in docStringNodes:
            name = docStringNode['@name']
            if name == 'recID':
              recId = docStringNode['#text']
              recFound = True
              count+=1
            if name == 'doi' and recFound:
              doi = docStringNode['#text']

          recMetadataUri =  metadataUriBase.replace('_URI_', recId)
          print recMetadataUri
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
                    try:
                      thisResource = Resource(uri=linkVal, lastmod = timestamp)
                      thisResource.link_set(rel="describedby", modified = timestamp, href = recMetadataUri)
                      print ' got this far '
                      thisResourceRecip = Resource(uri = recMetadataUri, lastmod = timestamp)
                      thisResourceRecip.link_set(rel="describes", href=linkVal, modified=timestamp)
                      thisResourceRecip.link_set(rel="profile", href="http://www.w3.org/2001/XMLSchema-instance")
                      print ' got farther '
                      rl.add([thisResource, thisResourceRecip])
                      resourceWritten = True
                      print 'resource added for ' + linkVal
                    except Exception as e: print str(e)

          if not resourceWritten: 
                thisResource = Resource(uri=recMetadataUri, lastmod = timestamp, mime_type="application/xml", )
                thisResource.link_set(rel="profile", href="http://www.w3.org/2001/XMLSchema-instance")
                try:
                  rl.add(thisResource)
                except Exception as e: print str(e)

        if count>=200:
          allFound = True
      except:
        pass

  response.writelines(rl.as_xml())
  response.flush()
  return HttpResponse(response, content_type="text/xml; charset=utf-8")

def changelist(response):
  response = HttpResponse()
  response.writable()

  cl = ChangeList()
  # solrResults = models.Results.results.get_queryset()

  queryField = 'title'
  queryString = settings.RESOURCESYNC_QUERY

  solr_timestamp = ''
  resourcelist_timestamp = ''
  changelist_timestamp = ''

  resourceList = dbLookup('resourcelist')
  resourcelist_refresh = resourceList.interval
  resourcelist_timestamp = resourceList.lower_bound
  changeList = dbLookup('changelist')
  changelist_timestamp = changeList.lower_bound

  cl.md_from = resourcelist_timestamp
  cl.md_until = changelist_timestamp

  from_timestamp = resourcelist_timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
  until_timestamp = changelist_timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
  solr_timestamp = '{' + from_timestamp + ' to ' + until_timestamp + '}'
  print 'changelist time query ' + solr_timestamp

  solrResults = models.Results.results.get_queryset(1000)
 
  for solrResult in solrResults:
     # a solrResult is a resultObj
     # a resultObj has following fields: recID, timestamp, doi, contentUri
     # if there is a contentUri, then describes, describedby
     try:
       thisResource = Resource(uri=solrResult['contentUri'], lastmod = solrResult['timestamp'], change='created')
       thisResource.link_set(rel="describedby", modified = timestamp, href = recMetadataUri)
       thisResourceRecip = Resource(uri =solrResult['recID'], lastmod=solrResult['timestamp'], change='created')
       thisResourceRecip.link_set(rel="describes", href=solrResult['contentUri'], modified=solrResult['timestamp'])
       thisResourceRecip.link_set(rel="profile", href="http://www.w3.org/2001/XMLSchema-instance")
       cl.add(thisResource)
       cl.add(thisResourceRecip)

     except:
        thisResource = Resource(uri=solrResult['recID'], lastmod = solrResult['timestamp'], mime_type="application/xml", change='created', timestamp=solrResult['timestamp'])
        thisResource.link_set(rel="profile", href="http://www.w3.org/2001/XMLSchema-instance")
        cl.add(thisResource)

  response.writelines(cl.as_xml())
  response.flush()
  return HttpResponse(response, content_type="text/xml; charset=utf-8")

