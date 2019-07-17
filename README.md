pyoaiharvester
==============

Simple command line oai-pmh harvester written in Python.

Usage
-----

Harvest a repository to a file named untsw.dc.xml

```
python pyoaiharvest.py -uri http://digital.library.unt.edu/explore/collections/UNTSW/oai/ -o untsw.dc.xml
```

Harvest the untl metadata format to a file named untsw.untl.xml

```
python pyoaiharvest.py -uri http://digital.library.unt.edu/explore/collections/UNTSW/oai/ -o untsw.untl.xml -m untl
```

Options
-----  

**-f**  
**--from**  
&nbsp;&nbsp;&nbsp;&nbsp; harvest records from this date, format: yyyy-mm-dd  

**-uri**  
**--baseURI**  
&nbsp;&nbsp;&nbsp;&nbsp; base URI of the repository  

**-dir**  
**--targetDir**  
&nbsp;&nbsp;&nbsp;&nbsp; target dir

**-max**  
**--maxRecNum**  
&nbsp;&nbsp;&nbsp;&nbsp; max num of records per file

**-rn**  
**--rootNode**  
&nbsp;&nbsp;&nbsp;&nbsp; root node to wrap the harvested oai records

**-fn**  
**--fileBaseName**  
&nbsp;&nbsp;&nbsp;&nbsp; base name of the target files 

**-m**  
**--mdprefix**  
&nbsp;&nbsp;&nbsp;&nbsp; use the specified metadata format, default="oai_dc"   

**-s**  
**--setName**  
&nbsp;&nbsp;&nbsp;&nbsp; harvest the specified set  

**-u**  
**--until**  
&nbsp;&nbsp;&nbsp;&nbsp; harvest records until this date, format: yyyy-mm-dd

**--lexBASE**
&nbsp;&nbsp;&nbsp;&nbsp; base relatet url escaping for '=()&:+'