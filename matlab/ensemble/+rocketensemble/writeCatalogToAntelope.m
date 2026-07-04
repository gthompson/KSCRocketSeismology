function out_dbpath = writeCatalogToAntelope(catalogobj, cfg)
%WRITECATALOGTOANTELOPE Write derived catalog to a copied Antelope DB.

[dbdir, dbname] = fileparts(cfg.DbPath);
if isempty(dbdir)
    dbdir = pwd;
end

out_dbpath = fullfile(cfg.WorkDir, sprintf('%s%s', dbname, cfg.ExportDbSuffix));

if ~exist(out_dbpath, 'file')
    try
        antelope.dbcp(cfg.DbPath, out_dbpath);
    catch ME
        warning('Could not copy source DB with antelope.dbcp: %s', ME.message);
    end
end

catalogobj.write('antelope', out_dbpath, 'overwrite');
end
