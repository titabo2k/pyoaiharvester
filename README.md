pyoaiharvester
==============

Simple command line oai-pmh harvester written in Python.

Usage
-----

```
python pyoaiharvest.py -uri 'http://oai.base-search.net/oai' \
-dir ./download \
-fn test_out.xml \
-max 10 \
-m 'base_dc' \
-s 'collection:ftjcie+(autoclasscode:(791 OR 659 OR 070 OR 175 OR 302 OR 770 OR 384 OR 002 OR 370))' \
--lexBASE
```

Options
-----  

**-uri**  
**--baseURI**  
&nbsp;&nbsp;&nbsp;&nbsp; base URI of the repository  

**-dir**  
**--targetDir**  
&nbsp;&nbsp;&nbsp;&nbsp; target dir

**-fn**  
**--fileBaseName**  
&nbsp;&nbsp;&nbsp;&nbsp; base name of the target files 

**-max**  
**--maxRecNum**  
&nbsp;&nbsp;&nbsp;&nbsp; max num of records per file

**-rn**  
**--rootNode**  
&nbsp;&nbsp;&nbsp;&nbsp; root node to wrap the harvested oai records

**-m**  
**--mdprefix**  
&nbsp;&nbsp;&nbsp;&nbsp; use the specified metadata format, default="oai_dc"   

**-s**  
**--setName**  
&nbsp;&nbsp;&nbsp;&nbsp; harvest the specified set  

**-f**  
**--from**  
&nbsp;&nbsp;&nbsp;&nbsp; harvest records from this date, format: yyyy-mm-dd  

**-u**  
**--until**  
&nbsp;&nbsp;&nbsp;&nbsp; harvest records until this date, format: yyyy-mm-dd

**--lexBASE**
&nbsp;&nbsp;&nbsp;&nbsp; base relatet url escaping for '=()&:+'