C* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
C*     CANDE-2025 Python Wrapper Entry Point                         *
C*     gfortran-compatible replacement for Cande_dll.f               *
C*                                                                   *
C*     Derived from CANDE_DLL in Cande_dll.f with Intel-specific     *
C*     extensions (DFLIB, DFWIN, VB callbacks, DEC$ attributes)      *
C*     removed for gfortran/f2py compilation.                        *
C* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
C
      SUBROUTINE RUN_CANDE(IFNAME2, IERROR)
C
Cf2py intent(in) IFNAME2
Cf2py intent(out) IERROR
C
C     IFNAME2 = file prefix (e.g. 'EX1' reads EX1.cid, writes EX1.out)
C     IERROR  = 0 on success, nonzero on error
C
      INCLUDE 'files.fi'
      INCLUDE 'pgroups.fi'
      INCLUDE 'xlrfd.fi'
      INCLUDE 'xlarge.fi'
      INCLUDE 'errstop.fi'
      INCLUDE 'inputCtrl.fi'
      INCLUDE 'dll_common.fi'
C
      CHARACTER*(*) IFNAME2
      INTEGER IERROR
C
      CHARACTER*8 CWORD(3), SOLVE(3), PLIST(7), XMETH(2), PTYPE
      INTEGER LENST
      INTEGER NLIST
      INTEGER NGLoc
      INTEGER NPMATDum
C
      REAL*8 PDIA, HTCVR(301), PIPMAT(5,2999),RESULT(20,2999),
     &       SK, SM
      INTEGER I, IA, ICHK00, ICHK01, ICHKM1, ICHKM2, ICOME,
     &        IEXIT, ISTOP, LOC2, MAXIT, N, NINC, NPCAN, NPIPE,
     &        NPMAT, NPPT
C
C     ---| Variables for READ statements
C
      CHARACTER*132  InpLine
      INTEGER        InpLen
      INTEGER        LENSTR
      INTEGER        GetInputLine
      CHARACTER*512  OutLine
      INTEGER        ILO
      INTEGER        InpFileLength
C
C     ---| String parameter for WrtTitle
C
      CHARACTER*80      SSTR
C
C     ---| Canned Title for Level 1 problems
C
      CHARACTER*4       TITLE1(17)
C
      DATA NLIST, PLIST/7, 'STEEL   ', 'ALUMINUM', 'CONCRETE ',
     &     'PLASTIC ', 'BASIC   ', 'CONRIB  ', 'CONTUBE '/
C
      DATA CWORD/'DESIGN  ', 'ANALYS  ', 'STOP    '/
      DATA SOLVE/'#1 BURNS', ' #2 AUTO', ' #3 USER'/
      DATA XMETH/' SERVICE', '    LRFD'/
      DATA MAXIT/30/
      DATA TITLE1/'LEVE','L-1 ','SOLU','TION','    ','    ',
     &            '    ','    ','    ','    ','    ','    ',
     &            '    ','    ','    ','    ','    '/
C
C     Initialize return code and DLL state for non-VB operation
C
      IERROR = 0
      SCREEN_MSGS_TO_VB_WINDOW = .FALSE.
      INPUT_PASSED_TO_DLL = .FALSE.
C
C     Set filenames from the prefix passed by Python
C
      InpFileLength = LENSTR(IFNAME2)
C
      InputFileName = IFNAME2(1:InpFileLength)//'.cid'
      OutputFileName = IFNAME2(1:InpFileLength)//'.out'
C
C     Table of contents file
C
      TOCFileName = IFNAME2(1:InpFileLength)//'.ctc'
      TOCLUN = 88
C
C     Log File Name
C
      LogFileName = IFNAME2(1:InpFileLength)//'.log'
      LogLUN = 89
C
C     XML file names and logical unit numbers
C
      XMLMeshGeomLUN = 85
      XMLMeshGeom = IFNAME2(1:InpFileLength)//'_MeshGeom.xml'
C
      XMLMeshResultsLUN = 86
      XMLMeshResults = IFNAME2(1:InpFileLength)//'_MeshResults.xml'
C
      XMLBeamResultsLUN = 87
      XMLBeamResults = IFNAME2(1:InpFileLength)//'_BeamResults.xml'
C
      NCHRPResultsLUN = 91
      NCHRPResults = IFNAME2(1:InpFileLength)//
     &                                     '_Process_1250.csv'
C
C     ALL DATA FILES ARE OPENED AND THEN CLOSED FROM THIS MAIN PROGRAM
C
      InpLUN = 5
      OutLUN = 6
C
      OPEN (InpLUN,FILE=InputFileName,STATUS='unknown')
      OPEN (OutLUN,FILE=OutputFileName,STATUS='unknown')
      OPEN (TOCLUN,FILE=TOCFileName,STATUS='unknown')
      OPEN (LogLUN,FILE=LogFileName,STATUS='unknown')
C
      OPEN (10,FILE=IFNAME2(1:InpFileLength)//
     &     '_PLOT1.dat',STATUS='unknown')
      OPEN (30,FILE=IFNAME2(1:InpFileLength)//
     &     '_PLOT2.dat',STATUS='unknown')
      OPEN (11,FILE=IFNAME2(1:InpFileLength)//
     &     '_DATA.dat',STATUS='REPLACE')
      OPEN (16,FILE=IFNAME2(1:InpFileLength)//
     &     '_DUNCAN.dat',STATUS='REPLACE')
      OPEN (17,FILE=IFNAME2(1:InpFileLength)//
     &     '_XFACES.dat',STATUS='REPLACE')
      OPEN (12,FILE=IFNAME2(1:InpFileLength)//
     &     '_FOR012.dat',FORM='UNFORMATTED')
      OPEN (13,FILE=IFNAME2(1:InpFileLength)//
     &     '_FOR013.dat',FORM='UNFORMATTED')
      OPEN (14,FILE=IFNAME2(1:InpFileLength)//
     &     '_FOR014.dat',FORM='UNFORMATTED')
      OPEN (15,FILE=IFNAME2(1:InpFileLength)//
     &     '_FOR015.dat',FORM='UNFORMATTED')
      OPEN (18,FILE=IFNAME2(1:InpFileLength)//
     &     '_FOR018.dat',FORM='UNFORMATTED')
C
      CALL PMSG('    Input file: '//InputFileName(1:80) )
      CALL PMSG('    Output file: '// OutputFileName(1:80))
C
      REWIND 30
C
C     WELCOME TO CANDE (First Message)
C
      NPROB = 0
      WRITE (OutLine,2001)
      ILO = MAX(1, LENSTR(OutLine))
      CALL PMSG(' ')
      CALL PMSG(' ')
      CALL PMSG(OutLine(1:ILO))
C
      WRITE (6,2000)
C
C     STARTING POINT FOR EACH NEW PROBLEM (BACK-TO-BACK)
C
 100  DO I = 1, 2999
         DO N = 1, 20
            RESULT(N,I) = 0.0
         ENDDO
      ENDDO
      PDIA = 0.0
      KPUTCK = 0
C
C     Read the input line into a string first
C
      IF (GetInputLine('A-1',InpLine, InpLen) .EQ. 0) THEN
      ELSE
         GOTO 10000
      ENDIF
C
      READ (InpLine(1:InpLen),1000,END=504,ERR=10000) XMODE, LEVEL,
     &                           LRFD, NPGRPS, HED, ITMAX, CULVERTID,
     &                           PROCESSID, SUBDID
      IF ( XMODE.EQ.CWORD(3) ) THEN
C
C     NORMAL EXIT FROM CANDE ("STOP" WORD IN DATA)
C
         WRITE (6,2500)
C
         WRITE (OutLine,2501)
         ILO = MAX(1, LENSTR(OutLine))
         CALL PMSG(' ')
         CALL PMSG(' ')
         CALL PMSG(' ')
         CALL PMSG(OutLine(1:ILO))
         GOTO 901
      ENDIF
C
C     PRINT AND CHECK INITIAL CONTROL DATA FOR CURRENT PROBLEM
C
      NPROB = NPROB + 1
C
      IF ( XMODE.EQ.CWORD(1) ) THEN
        ITDMAX = 20
        ITERD = 0
        DO N = 1, NPGRPS
          NGDSGN(N) = 0
        ENDDO
      ENDIF
C
      IF ( LEVEL.EQ.1 .OR. LEVEL.EQ.2 .OR. NPGRPS.LE.0 ) NPGRPS = 1
      IF ( LRFD.NE.1 ) LRFD = 0
      IF ( ITMAX.EQ.0 ) ITMAX = MAXIT
      IF ( ITMAX.LT.0 ) ISTOP = 0
      IF ( ITMAX.GT.0 ) ISTOP = 1
      WRITE (SSTR,2100) NPROB
      CALL WrtTitle(1,SSTR)
      WRITE (6,2101) HED, XMODE, SOLVE(LEVEL), XMETH(LRFD+1),
     &               NPGRPS, ITMAX
      IF (CULVERTID .GT. 0) THEN
         WRITE(6, 2102) CULVERTID, PROCESSID, SUBDID
      ENDIF
C
C     Write messages to the screen
C
      CALL PMSG(' ')
      CALL PMSG(' ')
      CALL PMSG1I('          *** PROBLEM NUMBER  %d',NPROB)
      CALL PMSG(' ')
      CALL PMSG(' ')
      CALL PMSG('Problem title: '//HED)
      CALL PMSG(' ')
      CALL PMSG(' ')
      CALL PMSG  ('          EXECUTION MODE ..................   '
     &                                                      //XMODE)
      CALL PMSG(' ')
C
      CALL PMSG  ('          SOLUTION LEVEL .................. '//
     &                                                     SOLVE(LEVEL))
      CALL PMSG (' ')
C
      CALL PMSG  ('          METHODOLOGY (LRFD OR SERVICE) ... '//
     &                                                    XMETH(LRFD+1))
      CALL PMSG(' ')
C
      CALL PMSG1I('          NUMBER OF PIPE-ELEMENT GROUPS ...     %d',
     &                                                           NPGRPS)
      CALL PMSG(' ')
C
      CALL PMSG1I('          MAXIMUM ITERATIONS PER STEP .....     %d',
     %                                                          ITMAX)
      CALL PMSG(' ')
C
      ITMAX = ABS(ITMAX)
C
      IF ( XMODE.NE.CWORD(1) .AND. XMODE.NE.CWORD(2) ) THEN
C
C     ERROR EXIT FOR BAD INPUT DATA IN MAIN PROGRAM
C
         WRITE (6,3000) XMODE
C
         CALL IERRMS(9035,
     &       'Input:RUN_CANDE:Invalid Design/Analysis Input = '//XMODE)
         CALL InputError
         GOTO 901
      ENDIF
      IF ( LEVEL.LT.1 .OR. LEVEL.GT.3 ) THEN
C
         WRITE (6,3005) LEVEL
C
         WRITE(OutLine, '(A, I3)')
     &       'Input:RUN_CANDE:Invalid Level Number = ', LEVEL
C
         CALL IERRMS(9036, OutLine)
         CALL InputError
         GOTO 901
      ENDIF
C
C     READ AND PROCESS ALL PIPE TYPE INPUTS FOR EACH GROUP
C
      NPMAT = 0
      NPPT = 0
C
      DO NGLoc = 1, NPGRPS
C
C     LEVEL 1 INPUT PROCESSING FOR PIPE TYPE
C
         IF ( LEVEL.EQ.1 ) THEN
            NG = 1
C
            IF (GetInputLine('A-2.L12',InpLine, InpLen) .EQ. 0) THEN
            ELSE
               GOTO 10000
            ENDIF
C
            READ (InpLine(1:InpLen),1010,ERR=10000) PTYPE
            NPIPE = 0
            DO N = 1, NLIST
               IF ( PTYPE.EQ.PLIST(N) ) NPIPE = N
            ENDDO
            IF ( NPIPE.EQ.0 ) GOTO 502
            NTYPEX(1) = NPIPE
C
            NPMAT = 10
            NPMAT1(1) = 1
            NPMAT2(1) = NPMAT
            NPMATX(1) = NPMAT
C
            NPPT = 11
            NPPT1(1) = 1
            NPPT2(1) = NPPT
C
            WRITE (6,2105) PLIST(NPIPE), NPPT
C
            CALL PMSG  (
     &           '          CULVERT PIPE-TYPE ............... '//
     &                                                   PLIST(NPIPE))
            CALL PMSG(' ')
C
            CALL PMSG1I(
     &           '          NUMBER OF PIPE POINTS SHOWN .....     %d',
     &                                                           NPPT)
            CALL PMSG(' ')
            GOTO 119
         ENDIF
C
C     LEVEL 2 INPUT PROCESSING FOR PIPE TYPE AND CANNED MESH
C
         IF ( LEVEL.EQ.2 ) THEN
            NG = 1
C
            IF (GetInputLine('A-2.L12',InpLine, InpLen) .EQ. 0) THEN
            ELSE
               GOTO 10000
            ENDIF
C
            READ (InpLine(1:InpLen),1010,ERR=10000) PTYPE, NPCAN
            IF ( NPCAN.LE.0 .OR. NPCAN.GE.4 ) GOTO 503
C
            NPIPE = 0
            DO N = 1, NLIST
               IF ( PTYPE.EQ.PLIST(N) ) NPIPE = N
            ENDDO
            IF ( NPIPE.EQ.0 ) GOTO 502
            NTYPEX(1) = NPIPE
C
C       SET NUMBER OF PIPE MATERIALS AND NODES FOR LEVEL 2 OPTIONS
C
            IF ( NPCAN.EQ.1 ) NPMAT = 10
            IF ( NPCAN.EQ.2 ) NPMAT = 14
            IF ( NPCAN.EQ.3 ) NPMAT = 19
            NPMAT1(1) = 1
            NPMAT2(1) = NPMAT
            NPMATX(1) = NPMAT
C
            NPPT = NPMAT + 1
            NPPT1(1) = 1
            NPPT2(1) = NPPT
C
            WRITE (6,2110) PLIST(NPIPE), NPCAN, NPMAT
C
            CALL PMSG(' ')
            CALL PMSG('          CULVERT PIPE-TYPE ............... '//
     &                                                    PLIST(NPIPE))
C
            CALL PMSG(' ')
            CALL PMSG1I(
     &           '          CANNED MESH CODE # ..............     %d',
     &                                                         NPCAN)
C
            CALL PMSG(' ')
            CALL PMSG1I(
     &           '          NUMBER OF BEAM ELEMENTS .........     %d',
     &                                                        NPMAT)
            GOTO 119
         ENDIF
C
C     FOR LEVEL 3, READ PTYPE GROUP(S) AND NUMBER OF ELEMENTS PER GROUP
C
         IF ( LEVEL.EQ.3 ) THEN
            NG = NGLoc
C
            IF (GetInputLine('A-2.L3',InpLine, InpLen) .EQ. 0) THEN
            ELSE
               GOTO 10000
            ENDIF
C
            READ (InpLine(1:InpLen),1010,ERR=10000) PTYPE, NPMATX(NGLoc)
            NPIPE = 0
            DO N = 1, NLIST
               IF ( PTYPE.EQ.PLIST(N) ) NPIPE = N
            ENDDO
            IF ( NPIPE.EQ.0 ) GOTO 502
            NTYPEX(NGLoc) = NPIPE
            NPMAT = NPMAT + NPMATX(NGLoc)
            NPMAT1(NGLoc) = NPMAT - NPMATX(NGLoc) + 1
            NPMAT2(NGLoc) = NPMAT
C
            NPPT = NPPT + (NPMATX(NGLoc)+1)
            NPPT1(NGLoc) = NPPT - (NPMATX(NGLoc)+1) + 1
            NPPT2(NGLoc) = NPPT
C
            IF(NPGRPS.GT.1) THEN
              WRITE (6,2112)
              WRITE(SSTR, 2113) NGLoc
              CALL WrtTitle(2,SSTR)
            ENDIF
            WRITE (6,2115) PLIST(NPIPE), NPMATX(NGLoc)
         ENDIF
C
C     READ OR ESTABLISH PIPE PROPERTIES FROM PIPE LIBRARY, ALL LEVELS
C
 119     ICOME = 1
         NPIPE = NTYPEX(NG)
C
         IF ( NPIPE.EQ.1 ) CALL STEEL(IA,ICOME,IEXIT,LEVEL,NINC,NPMAT,
     &                                NPPT,PDIA,PIPMAT,RESULT,SK,SM,
     &                                HTCVR,XMODE)
         IF ( NPIPE.EQ.2 ) CALL ALUMIN(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 SK,SM,XMODE)
         IF ( NPIPE.EQ.3 ) CALL CONCRE(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 XMODE)
         IF ( NPIPE.EQ.4 ) CALL PLASTI(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 SK,SM,HTCVR,XMODE)
         IF ( NPIPE.EQ.5 ) CALL BASIC(IA,ICOME,IEXIT,LEVEL,NINC,NPMAT,
     &                                NPPT,PDIA,PIPMAT,RESULT,XMODE)
         IF ( NPIPE.EQ.6 ) CALL CONRIB(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 XMODE)
         IF ( NPIPE.EQ.7 ) CALL CONTUBE(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 XMODE)
C
C     CHECK IF THERE WAS INPUT ERROR IN PIPE SUBROUTINES, KPUTCK > 0.
C     EXIT PROGRAM IF INPUT ERROR WAS DETECTED
C
         IF ( KPUTCK.GT.0 ) THEN
            WRITE (6,4000) PTYPE
            CALL IERRTX(' ')
            CALL IERRTX(' ')
            CALL IERRTX(' ')
            CALL IERRMS(9037,
     &               'Input:RUN_CANDE: Error for Pipe-Type = '//PTYPE)
            GOTO 901
         ENDIF
C
      ENDDO
      WRITE (6,2125)
C
C     READ SOIL AND SYSTEM PROPERTIES FROM SOLUTION LIBRARY
C
      WRITE (6,2130)
      CALL WrtTitle(1,'  REVIEW SYSTEM INPUT DATA')
C
      IF ( LEVEL.EQ.1 ) THEN
        CALL BURNS(IA,ICOME,IEXIT,NINC,NPMAT,NPPT,PDIA,
     &             PIPMAT,RESULT,SK,SM,HTCVR)
C
C       Write the beam data to GUI file for beam graphs
C
        CALL BMResultsXML(0, NINC, NPMAT, NPPT, TITLE1, NPGRPS,
     &                    NTYPEX, NPMATX, NPMAT1, NPMAT2, NPPT1,
     &                    NPPT2, RESULT)
      ENDIF
C
      IF ( LEVEL.EQ.2 .OR. LEVEL.EQ.3 )
     &     CALL PRHERO(IA,ICOME,IEXIT,NINC,NPMAT,NPPT,NPCAN,LEVEL,
     &     PDIA,PIPMAT,RESULT,SK,SM,HTCVR)
C
C     CHECK IF THERE WAS INPUT ERROR IN LEVEL 1,2 OR 3 SUBROUTINES,
C     EXIT PROGRAM IF INPUT ERROR WAS DETECTED (KPUTCK > 0)
C
      IF ( KPUTCK.GT.0 ) THEN
         WRITE (6,4500) LEVEL
         CALL IERRTX(' ')
         CALL IERRTX(' ')
         CALL IERRTX(' ')
         WRITE(OutLine,'(A,I2)')
     &        'Input:RUN_CANDE: Error for LEVEL = ',LEVEL
         CALL IERRMS(9038, OutLine)
         GOTO 901
      ENDIF
C
C     CHECK IF USER REQUESTED DATA CHECK ONLY, NO EXECUTION.
C
      IF ( NPUTCK.GT.0 ) THEN
         WRITE (6,2200) NPROB
         CALL PMSG(' ')
         CALL PMSG(' ')
         CALL PMSG('USER REQUESTED DATA CHECK ONLY, NO EXECUTION FOR')
         CALL PMSG1I('   PROBLEM # = %d', NPROB)
         GOTO 100
      ENDIF
C
C
C *** END OF INPUT PHASE (ICOME= 1), START SOLUTION PHASE (ICOME = 2)
C
C     SOLVE SYSTEM FOR ALL RESPONSES, ITERATE AS REQUIRED.
C
      IEXIT = 1
      ITERD = 1
C
 140  ICOME = 2
      IOVER = 0
C
C     PRINT OUT MONITOR TRACE OF SOLUTION PROCESS
C
      IF ( IA.EQ.0 ) THEN
         CALL PMSG(' ')
         CALL PMSG(' ')
         CALL PMSG('      TRACK SOLUTION PROGRESS')
         CALL PMSG(' ')
         CALL PMSG('      LOAD-STEP     EXIT-CODE     ITERATION')
      ENDIF
C
      IF ( LEVEL.EQ.1 ) CALL BURNS(IA,ICOME,IEXIT,NINC,NPMAT,NPPT,
     &                             PDIA,PIPMAT,RESULT,SK,SM,HTCVR)
      IF ( LEVEL.EQ.2 .OR. LEVEL.EQ.3 )
     &     CALL PRHERO(IA,ICOME,IEXIT,NINC,NPMAT,NPPT,NPCAN,LEVEL,
     &     PDIA,PIPMAT,RESULT,SK,SM,HTCVR)
C
C     EVALUATE PIPE RESPONSES AND UPDATE MODELS
C
      ICHKM2 = 0
      ICHKM1 = 0
      ICHK00 = 0
      ICHK01 = 0
      DO NGLoc = 1, NPGRPS
         NG = NGLoc
         NPIPE = NTYPEX(NGLoc)
         IF ( NPIPE.EQ.1 ) CALL STEEL(IA,ICOME,IEXIT,LEVEL,NINC,NPMAT,
     &                                NPPT,PDIA,PIPMAT,RESULT,SK,SM,
     &                                HTCVR,XMODE)
         IF ( NPIPE.EQ.2 ) CALL ALUMIN(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 SK,SM,XMODE)
         IF ( NPIPE.EQ.3 ) CALL CONCRE(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 XMODE)
         IF ( NPIPE.EQ.4 ) CALL PLASTI(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 SK,SM,HTCVR,XMODE)
         IF ( NPIPE.EQ.5 ) CALL BASIC(IA,ICOME,IEXIT,LEVEL,NINC,NPMAT,
     &                                NPPT,PDIA,PIPMAT,RESULT,XMODE)
         IF ( NPIPE.EQ.6 ) CALL CONRIB(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 XMODE)
         IF ( NPIPE.EQ.7 ) CALL CONTUBE(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 XMODE)
C
         IF ( IEXIT.EQ.-2 ) ICHKM2 = ICHKM2 + 1
         IF ( IEXIT.EQ.-1 ) ICHKM1 = ICHKM1 + 1
         IF ( IEXIT.EQ.0 ) ICHK00 = ICHK00 + 1
         IF ( IEXIT.EQ.1 ) ICHK01 = ICHK01 + 1
C
      ENDDO
C
C     CHECK IF ITERATION LIMIT HAS BEEN REACHED.
C
      IF ( IOVER.GT.0 ) THEN
         WRITE (6,5000) ITMAX, IA
         CALL PMSG2I(' *** ITERATION LIMIT = %d, EXCEEDED ON STEP = %d'
     &               ,ITMAX,IA)
         IF ( ISTOP.EQ.1 ) THEN
            WRITE (6,5010)
            CALL PMSG(' ')
            CALL PMSG('      PROGRAM WILL STOP. ')
            CALL PMSG('      (NOTE: USER HAS CONTROL VIA INPUT'//
     &                                      ' PARAMETER ITMAX)')
            CALL PMSG('      SEE 2024 USER MANUAL SECTION 4.3.4 FOR'//
     &                      ' GUIDANCE ON NON-CONVERGED SOLUTIONS.')
            GOTO 901
         ELSEIF ( ISTOP.NE.1 ) THEN
            WRITE (6,5020)
            CALL PMSG(' ')
            CALL PMSG('      PROGRAM WILL CONTINUE TO NEXT LOAD STEP '
     &                    //'DUE TO INPUT CHOICE -ITMAX.')
            CALL PMSG('      SOLUTIONS FOR THIS LOAD STEP SHOULD'//
     &                          ' BE VIEWED WITH CAUTION.')
            CALL PMSG('      SEE 2024 USER MANUAL SECTION 4.3.4 FOR'//
     &                      ' GUIDANCE ON NON-CONVERGED SOLUTIONS.')
            IEXIT = 0
            NINC = ABS(NINC)
            IF ( IA.GE.NINC ) IEXIT = 1
            GOTO 200
         ENDIF
      ENDIF
C
C     DETERMINE THE OVERALL CONTROLLING VALUE FOR IEXIT
C
      IF ( ICHKM2.GT.0 ) THEN
         IEXIT = -2
         ITERD = ITERD + 1
         IDALL = 0
         DO N = 1, NPGRPS
           IF(NGDSGN(N) .EQ. 1) IDALL = IDALL + 1
         ENDDO
C
         WRITE (OutLine,2117) IA, IEXIT, ITERCNT
         CALL PMSG(OutLine)
         GOTO 140
      ELSEIF ( ICHKM1.GT.0 ) THEN
         IEXIT = -1
C
         WRITE (OutLine,2117) IA, IEXIT, ITERCNT
         CALL PMSG(OutLine)
         GOTO 140
      ELSEIF ( ICHK00.EQ.NPGRPS ) THEN
         IEXIT = 0
         WRITE (OutLine,2117) IA, IEXIT, ITERCNT
         CALL PMSG(OutLine)
      ELSEIF ( ICHK01.EQ.NPGRPS ) THEN
         IEXIT = 1
         WRITE (OutLine,2117) IA, IEXIT, ITERCNT
         CALL PMSG(OutLine)
      ENDIF
C
C     PRINT THE LOAD STEP (IEXIT=0 OR 1) FOR FEM DATA AND PIPE GROUPS
C
 200  ICOME = 3
C
C     PRINT FEM DATA AND COMPUTE BUCKLING FACTOR IF REQUIRED.
C     (WE DON'T PRINT FEM DATA FROM DESIGN MODE,SET ICOME = -3).
C
      IF ( XMODE.EQ.CWORD(1) ) ICOME = -3
C
      IF (IA.EQ.1 .AND. ICOME.EQ.3) THEN
            WRITE(6,2118)
            CALL WrtTitle(1,'  SOLUTION OUTPUT RESULTS')
      ENDIF
C
      IF ( LEVEL.EQ.1 .AND. ICOME.EQ.3) THEN
            WRITE(6,2118)
            WRITE(SSTR, 2121) IA
            CALL WrtTitle(2,SSTR)
            WRITE(6,2120)
C
C       Write the beam results to the XML file for GUI graph
C
           NPMATDum = 0
           CALL BMResultsXML(IA, NINC, NPMATDum, NPPT, TITLE1, NPGRPS,
     &                       NTYPEX, NPMATX, NPMAT1, NPMAT2, NPPT1,
     &                       NPPT2, RESULT)
      ENDIF
C
      IF ( LEVEL.EQ.2 .OR. LEVEL.EQ.3 ) THEN
         IF ( ICOME.EQ.3 ) THEN
            WRITE(6,2118)
            WRITE(SSTR, 2119) IA
            CALL WrtTitle(2,SSTR)
            WRITE(6,2120)
         ENDIF
         CALL PRHERO(IA,ICOME,IEXIT,NINC,NPMAT,NPPT,NPCAN,LEVEL,PDIA,
     &               PIPMAT,RESULT,SK,SM,HTCVR)
      ENDIF
      ICOME = 3
C
C     PRINT STRUCTURAL RESPONSES FROM PIPE ROUTINES.
C
      DO NGLoc = 1, NPGRPS
         NG = NGLoc
         IF ( XMODE.NE.CWORD(1) ) WRITE (6,2125)
         NPIPE = NTYPEX(NGLoc)
         IF ( NPIPE.EQ.1 ) CALL STEEL(IA,ICOME,IEXIT,LEVEL,NINC,NPMAT,
     &                                NPPT,PDIA,PIPMAT,RESULT,SK,SM,
     &                                HTCVR,XMODE)
         IF ( NPIPE.EQ.2 ) CALL ALUMIN(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 SK,SM,XMODE)
         IF ( NPIPE.EQ.3 ) CALL CONCRE(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 XMODE)
         IF ( NPIPE.EQ.4 ) CALL PLASTI(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 SK,SM,HTCVR,XMODE)
         IF ( NPIPE.EQ.5 ) CALL BASIC(IA,ICOME,IEXIT,LEVEL,NINC,NPMAT,
     &                                NPPT,PDIA,PIPMAT,RESULT,XMODE)
         IF ( NPIPE.EQ.6 ) CALL CONRIB(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 XMODE)
         IF ( NPIPE.EQ.7 ) CALL CONTUBE(IA,ICOME,IEXIT,LEVEL,NINC,
     &                                 NPMAT,NPPT,PDIA,PIPMAT,RESULT,
     &                                 XMODE)
      ENDDO
C
C     COMPUTE NEXT LOAD STEP IF IEXIT = 0,
C
      IF ( IEXIT.EQ.0 ) THEN
         ICOME = 2
         GOTO 140
      ENDIF
C
C     OTHERWISE READ A NEW PROBLEM (IEXIT = 1)
C
      ICOME = 1
      GOTO 100
C
 502  WRITE (6,3010) PTYPE
      CALL IERRTX(' ')
      CALL IERRTX(' ')
      CALL IERRTX(' ')
      CALL IERRMS(9039, 'Input:RUN_CANDE: *** STOP, INVALID'//
     &                                 ' PIPE-TYPE NAME ='//PTYPE)
      GOTO 901
C
 503  WRITE (6,3020) NPCAN
      CALL IERRTX(' ')
      CALL IERRTX(' ')
      CALL IERRTX(' ')
      WRITE(OutLine,'(A,I3)') 'Input:RUN_CANDE: *** STOP, INVALID'//
     &                                        ' CANNED MESH NUMBER =',
     &                                                         NPCAN
      CALL IERRMS(9040,OutLine)
      GOTO 901
C
 504  WRITE (6,3030)
      CALL IERRTX(' ')
      CALL IERRTX(' ')
      CALL IERRTX(' ')
C
      CALL IERRMS(9041,'Input:RUN_CANDE: *** STOP, END OF FILE'//
     &                               ' ENCOUNTERED ON FIRST INPUT')
C
C     CLOSE ALL FILES AND STOP (APPLIES TO NORMAL AND ERROR EXIT)
C
 901  CLOSE (InpLUN,STATUS='KEEP')
      CLOSE (OutLUN,STATUS='KEEP')
      CLOSE (TOCLUN)
      CLOSE (LogLUN)
      CLOSE (10,STATUS='KEEP')
      CLOSE (30,STATUS='KEEP')
      CLOSE (11,STATUS='DELETE')
      CLOSE (16,STATUS='DELETE')
      CLOSE (17,STATUS='DELETE')
      CLOSE (12,STATUS='DELETE')
      CLOSE (13,STATUS='DELETE')
      CLOSE (14,STATUS='DELETE')
      CLOSE (15,STATUS='DELETE')
      CLOSE (18,STATUS='DELETE')
C
      RETURN
C
C     Input Line Error
10000 CONTINUE
      CALL InputError
      IERROR = 1
      GOTO 901
C
C     INPUT FORMATS
C
 1000 FORMAT (A8,1X,I1,I2,I3,A60,I5,I5,I5,I5)
 1010 FORMAT (A8,2X,I5)
C
C     OUTPUT FORMATS
C
 2000 FORMAT (//,11X,
     &  '*** WELCOME TO CANDE-2025 (Version April 2025) ***',///)
 2001 FORMAT (10X,
     &  '*** WELCOME TO CANDE-2025 (Version April 2025) ***')
 2100 FORMAT (' MASTER CONTROL AND PIPE-TYPE DATA FOR PROBLEM #',I3)
 2101 FORMAT  (///,10X,'USER TITLE: ',A60,///,10X,
     &        'EXECUTION MODE .................. ',2X,A8,//,10X,
     &        'SOLUTION LEVEL .................. ',A8,//,10X,
     &        'METHODOLOGY (LRFD OR SERVICE) ... ',A8,//,10X,
     &        'NUMBER OF PIPE-ELEMENT GROUPS ....',I8,//,10X,
     &        'MAXIMUM ITERATIONS PER STEP ......',I8,//)
 2102 FORMAT  (///,10X,'NCHRP PROCESS 12-50 OUTPUT SPECIFIED',//10X,
     &        'CULVERT ID .......................',I8,//,10X,
     &        'PROCESS ID .......................',I8,//,10X,
     &        'SUBDOMAIN ID .....................',I8,//)
C
 2105 FORMAT (/,10X,'CULVERT PIPE-TYPE ............... ',A8,//,10X,
     &        'NUMBER OF PIPE POINTS SHOWN ..... ',I8)
 2110 FORMAT (//,10X,'CULVERT PIPE-TYPE ............... ',A8,//,10X,
     &        'CANNED MESH CODE # .............. ',I8,//,10X,
     &        'NUMBER OF BEAM ELEMENTS ......... ',I8)
 2112 FORMAT (///,40(' -'),//)
 2113 FORMAT ('  PIPE-TYPE PROPERTIES FOR GROUP # ',I2)
 2115 FORMAT (/,10X,'PIPE ELEMENT TYPE ............... ',A8,//,10X,
     &        'NUMBER OF BEAM ELEMENTS ......... ',I8)
 2117 FORMAT (10X,I5,9X,I5,9X,I5)
C
 2118 FORMAT (//,40(' +'),//)
 2119 FORMAT ('  FINITE ELEMENT OUTPUT FOR LOAD STEP',I3)
 2120 FORMAT (//,40(' +'))
 2121 FORMAT ('  LEVEL 1 OUTPUT FOR LOAD STEP',I3)
 2125 FORMAT (//,40(' -'))
 2130 FORMAT (//)
 2200 FORMAT (////,' USER REQUESTED DATA CHECK ONLY, NO EXECUTION FOR',
     &        /,' PROBLEM # =',I3)
 2500 FORMAT (//////10X,' * * * * NORMAL EXIT FROM CANDE * * * * ')
 2501 FORMAT (10X,' * * * * NORMAL EXIT FROM CANDE * * * * ')
C
C     ERROR FORMATS
C
 3000 FORMAT (////,' *** STOP, INVALID XMODE NAME =',A8)
 3005 FORMAT (////,' *** STOP, INVALID LEVEL NUMBER =',I3)
 3010 FORMAT (////,' *** STOP, INVALID PIPE-TYPE NAME =',A8)
 3020 FORMAT (////,' *** STOP, INVALID CANNED MESH NUMBER =',I3)
 3030 FORMAT (////,' *** STOP, END OF FILE ENCOUNTERED ON FIRST INPUT')
C
 4000 FORMAT (////,' *** STOP, INPUT DATA ERROR FOR PIPE-TYPE =',A8)
 4500 FORMAT (////,' *** STOP, INPUT DATA ERROR FOR LEVEL =',I2)
C
 5000 FORMAT (////,' *** ITERATION LIMIT =',I3,', EXCEEDED ON STEP =',
     &        I3)
 5010 FORMAT (/,'      PROGRAM WILL STOP. ',
     &        ' (NOTE: USER HAS CONTROL VIA INPUT PARAMETER ITMAX)',/,
     &        ' SEE 2024 USER MANUAL SECTION 4.3.4 FOR GUIDANCE',
     &        ' ON NON-CONVERGED SOLUTIONS.')
 5020 FORMAT (/,'      PROGRAM WILL CONTINUE TO NEXT LOAD STEP ',
     &        'DUE TO INPUT CHOICE OF -ITMAX.',/,
     &        ' SEE 2024 USER MANUAL SECTION 4.3.4 FOR GUIDANCE',
     &        ' ON NON-CONVERGED SOLUTIONS.')
      END
