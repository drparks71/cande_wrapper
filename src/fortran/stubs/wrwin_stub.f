C* wrwin_stub.f - gfortran replacement for Intel/Wrwin.for
C* Writes output to stdout instead of VB window.
C*
      SUBROUTINE WRWIN(OUTSTR)
C
      INCLUDE 'dll_common.fi'
      INCLUDE 'files.fi'
C
      CHARACTER*(*) OUTSTR
      INTEGER       LENSTR
      INTEGER       LO
C
      LO = MAX(1, LENSTR(OUTSTR))
C
C     Always write to console (no VB window in gfortran build)
      WRITE (*,'(A)') '>>'//OUTSTR(1:LO)
C
C     Also write to log file if open
      IF (LogLUN .GT. 0) THEN
         WRITE (LogLUN,'(A)',ERR=10) OUTSTR(1:LO)
      ENDIF
C
   10 CONTINUE
      RETURN
      END
