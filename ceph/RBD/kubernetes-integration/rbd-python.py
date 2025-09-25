with open("/dev/rbd0", "rb+") as f: 
  
    data = b"Hello Ceph RBD from Python!\n" 
    f.write(data) 
  

    f.seek(0) 
  

    content = f.read(len(data)) 
    print("Read from RBD:", content.decode()) 
 
