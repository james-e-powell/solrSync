# solrSync
This is a DJango-based prototype which can generate ResourceSync resourcelist and changelist from a Solr index. Interaction with Solr is handled by methods in models.py, which rendering the results as a ResourceSync list is handled in views.py. When Django is started, these items are accessed via http://hostname:port/resourcelist.xml or http://hostname:port/changelist.xml. Initial settings are configurable in settings.py. Subsequently, a small amount of data is stored in a sqllite db. This application uses the [resync library][https://github.com/resync/resync].

Currently only the list date value for resourcelist is used. The resourcelist list date is picked up from settings.py and stored here. Every subsequent request for a resourcelist uses this date as the "until" value. The changelist is open, so every request for a changelist delivers a list with this same date as the "from" value. Any items with a timestamp after this date will be returned in the changelist. 

Since anyone who deploys Solr has great flexibility in terms of how and what they index, you will probably have to make changes to the models.py method called get_queryset, which is part of the ResultsManager class. This method parses a Solr results set and maps the fields needed by solrSync to produce ResourceSync resource and changelists. 

This tool will not work if there is not a timestamp field and a unique identifier per doc entry in the Solr results set. You will have to modify models.py to reflect the element or attribute name for the timestamp field in your Solr index.  You will also need to modify the code so that reciprocal metadata / content links are identified and extracted. This is where your Solr index may differ dramatically from ours. We use the recID field together with a base URL to construct a metadata URI. Our full text URI is stored in a <str> child of an <arr> element with a name attribute assigned the value "url" (see below). In many cases, we have no full text, but since our initial use case for the resource and changelist is to discover full text for items that lack it, these are the resources we are most interested in. You will definitely also need to modify the Solr query string so that it points to your Solr instance, and so that the query elements correspond to your Solr indexed fields.

Here's what our Solr results set looks like:

*Solr results header information*
```
    <?xml version="1.0" encoding="UTF-8"?>
    <response>

    <lst name="responseHeader">
      <int name="status">0</int>
      <int name="QTime">52</int>
      <lst name="params">
        <str name="sort">recID asc</str>
        <str name="indent">true</str>
        <str name="q">title:* AND timestamp:[* TO 2016-10-03T22:11:39Z]</str>
        <str name="cursorMark">*</str>
        <str name="wt">xml</str>
      </lst>
    </lst>
    <result name="response" numFound="26469" start="0">
```

*A Solr `<doc>` entry, metadata only*
```
  <doc>
    <str name="recID">info:lanl-repo/lapr/LAPR-2007-000001</str>
    <str name="dataset">LAPR</str>
    <str name="displayName">Perelson, Alan S. ; Bragg, Jason G. ; Wiegel, Frederi
k W.</str>
    <str name="displayTitle">The complexity of the immune system: Scaling laws</s
tr>
    <arr name="publication">
      <str>Complex Systems Science in BioMedicine</str>
    </arr>
    <arr name="publication_browse">
      <str>Complex Systems Science in BioMedicine</str>
    </arr>
    <arr name="publication_rbrowse">
      <str>Xlnkovc Hbhgvnh Hxrvmxv rm YrlNvwrxrmv</str>
    </arr>
    <str name="displaySource">Complex Systems Science in BioMedicine ; p.451-459,
 2006</str>
    <str name="peerreview">Unconfirmed</str>
    <long name="_version_">1522819396678975488</long>
    <date name="timestamp">2016-01-08T17:22:26.983Z</date></doc>
```
*A Solr `<doc>` entry with metadata and full content links*
```
  <doc>
    <str name="recID">info:lanl-repo/lareport/LA-05780-MS</str>
    <str name="dataset">LAauthors</str>
    <str name="displayName">Purtymun, William D. ; West, Francis G. ; Pettitt, Ro
land A.</str>
    <str name="displayTitle">GEOLOGY OF GEOTHERMAL TEST HOLE GT - 2 FENTON HILL S
ITE, JULY 1974.</str>
    <arr name="collection">
      <str>Hot Dry Rock</str>
    </arr>
    <str name="displaySource">LA-05780-MS ; 21-oct-1974</str>
    <arr name="url">
      <str>Report | http://permalink.lanl.gov/object/tr?what=info:lanl-repo/larep
ort/LA-05780-MS</str>
    </arr>
    <long name="_version_">1530147539828867072</long>
    <date name="timestamp">2016-03-29T14:40:09.037Z</date></doc>
```
