C* cmdparse_stub.f - gfortran replacement for Intel/CMDPARSE.FOR
C* No-op: when called from Python, the filename is passed directly
C* so command-line parsing is not needed.
C*
      SUBROUTINE CMDPARSE(NSTR, CLNARY, NCLNARY, RC)
C
      CHARACTER*(*) CLNARY(10)
      INTEGER       NCLNARY(10)
      INTEGER       NSTR
      INTEGER       RC
C
C     Return zero arguments - filename is passed from Python
      NSTR = 0
      RC = 0
C
      RETURN
      END
