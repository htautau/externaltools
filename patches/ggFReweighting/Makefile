OBJ=ggFReweighting.o

CXX=g++

CXXFLAGS=-g -Wall

INCLUDEFLAGS=-I../

ROOTCFLAGS = $(shell root-config --cflags)

.SUFFIXES:      .cxx .h

libggFReweighting.a: $(OBJ)
	ar -rs libggFReweighting.a ./*o

.cxx.o:
	$(CXX) $(CXXFLAGS) $(ROOTCFLAGS) $(INCLUDEFLAGS) -c $<

clean:
	rm ./*.o; rm *.a

# DO NOT DELETE
ggFReweighting.o: ggFReweighting.h
