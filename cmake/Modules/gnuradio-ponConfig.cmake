find_package(PkgConfig)

PKG_CHECK_MODULES(PC_GR_PON gnuradio-pon)

FIND_PATH(
    GR_PON_INCLUDE_DIRS
    NAMES gnuradio/pon/api.h
    HINTS $ENV{PON_DIR}/include
        ${PC_PON_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    GR_PON_LIBRARIES
    NAMES gnuradio-pon
    HINTS $ENV{PON_DIR}/lib
        ${PC_PON_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/gnuradio-ponTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(GR_PON DEFAULT_MSG GR_PON_LIBRARIES GR_PON_INCLUDE_DIRS)
MARK_AS_ADVANCED(GR_PON_LIBRARIES GR_PON_INCLUDE_DIRS)
