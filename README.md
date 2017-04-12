# solrSync
[ResourceSync](http://www.openarchives.org/rs/toc) is a Web content replication and synchronization standard. With ResourceSync, a source provides information about content that it makes available for replication, as well as information about subsequent changes to that content. A destination that wants to stay in sync with that source can retrieve this information in order to do so. The information exposed by the source is usually metadata and the objects described by that metadata. There are a variety of ways that a source can provide this information, including resourcelists, changelists, resource dumps, change dumps, change  notifications, etc. This prototype dynamically generates a resourcelist and an open changelist on behalf of a source. It is a DJango-based application that stands apart from the source. The resourcelist and changelist  are generated on the fly from a local or remote Solr index. There are three addressable URLs in urls.py: changelist.xml, resourcelist.xml, and an administrative view of solrSync Settings available at resourcesync. 

solrSync produces a resourcelist that includes content in the Solr index up to the date set in the settings file. This value is subsequently stored in a dbsql lite table so that subsequent requests for a esourcelist use the same timestamp. An open changelist also uses this date as a starting point. Thus the resourcelist.xml represents everything until the timestamp, and the changelist.xml contains everything from that timestamp value to the present.

The views.py file has a pair of methods that correspond to resourcelist and changelist. They submit a request using the above mentioned timestamp through a method in the models.py file to Solr. The get_queryset method submits the Solr query, requests multiple pages of results if needed, parses the Solr results doc and returns a list of Python objects that represent the fields necessary to generate a resource or changelist <loc> entry. The methods in the views.py file itereate through this list of python objects and create a ResourceList or ChangeList object using the [resync library](https://github.com/resync/resync), populating it with values from the model, and returning an XML version of the appropriate list object upon completion..


Since anyone who deploys Solr has great flexibility in terms of how and what they index, you will probably have to make changes to the models.py method called get_queryset, which is part of the ResultsManager class. This method parses a Solr results set and maps the fields needed by solrSync to produce ResourceSync resource and changelists. 

You may not be able to use this tool as-is if there is not a timestamp field and a unique identifier per doc entry in your Solr results set. You will have to modify models.py to reflect the element or attribute name for the timestamp field in your Solr index.  You will also need to modify the code so that reciprocal metadata / content links are identified and extracted. This is where your Solr index may differ dramatically from ours. We use the recID field together with a base URL to construct a metadata URI. Our full text URI is stored in a <str> child of an <arr> element with a name attribute assigned the value "url" (see below). In many cases, we have no full text, but since our initial use case for the resource and changelist is to discover full text for items that lack it, these are the resources we are most interested in. You will definitely also need to modify the Solr query string so that it points to your Solr instance, and so that the query elements correspond to your Solr indexed fields.

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
